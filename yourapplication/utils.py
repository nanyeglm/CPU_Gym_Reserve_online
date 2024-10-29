# yourapplication/utils.py

import asyncio
import aiohttp
import time
import logging
from bs4 import BeautifulSoup
from threading import Thread
from flask import current_app
from yourapplication.models import db, Order, Reservation
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime

# 启动后台更新任务
def start_background_tasks(app):
    # 启动一个线程不断运行更新任务
    def run_update():
        with app.app_context():
            while True:
                try:
                    update_database(app)  # 调用更新数据库的函数
                except Exception as e:
                    app.logger.error(f"后台更新任务出错：{e}")  # 记录错误日志
                time.sleep(180)  # 每隔3分钟运行一次

    thread = Thread(target=run_update)
    thread.daemon = True
    thread.start()  # 启动后台线程

# 更新数据库的函数
def update_database(app):
    app.logger.info("开始更新数据库")

    # 检查并清理过期数据
    clean_old_data(app)

    # 获取数据库中最大的 yuyue_id，如果不存在则设为 823
    max_yuyue_id = db.session.query(db.func.max(Order.yuyue_id)).scalar() or 823
    # 使用异步获取新的订单数据，范围为 max_yuyue_id + 1 到 max_yuyue_id + 100
    new_orders = asyncio.run(fetch_new_orders(app, max_yuyue_id + 1, max_yuyue_id + 100))

    # 插入新的订单到数据库
    insert_new_orders(app, new_orders)
    
    # 检查现有订单状态并清理已取消的订单
    check_existing_orders(app)

    app.logger.info("数据库更新完成")

# 清理早于今天的旧数据
def clean_old_data(app):
    today = datetime.now().strftime('%Y-%m-%d')
    try:
        old_orders = Order.query.filter(Order.date < today).all()
        old_reservations = Reservation.query.filter(Reservation.date < today).all()
        
        # 删除找到的旧数据
        for order in old_orders:
            db.session.delete(order)
        for reservation in old_reservations:
            db.session.delete(reservation)

        db.session.commit()
        app.logger.info(f"已清理早于 {today} 的旧数据")
    except SQLAlchemyError as e:
        db.session.rollback()  # 出现错误时回滚
        app.logger.error(f"清理旧数据时出错：{e}")

# 异步获取新订单数据
async def fetch_new_orders(app, start_id, end_id):
    tasks = []
    async with aiohttp.ClientSession() as session:
        # 创建获取每个订单的任务列表
        for yuyue_id in range(start_id, end_id):
            tasks.append(fetch_order(app, session, yuyue_id))
        results = await asyncio.gather(*tasks)  # 并发执行所有任务
    return [result for result in results if result]  # 过滤掉 None 的结果

# 异步获取单个订单的函数，带重试机制
async def fetch_order(app, session, yuyue_id, retries=5, delay=1):
    url = f"http://cgyytyb.cpu.edu.cn/wap/yuyueIn?id={yuyue_id}"
    headers = app.config['HEADERS']  # 从配置中获取请求头
    for attempt in range(retries):
        try:
            # 发起 GET 请求获取订单内容
            async with session.get(url, headers=headers, timeout=20) as response:
                content = await response.text()
                order_data = extract_order_info(app, yuyue_id, content)  # 提取订单信息
                await asyncio.sleep(0.1)  # 控制请求频率，防止请求过多
                return order_data
        except asyncio.TimeoutError:
            app.logger.error(f"获取订单 {yuyue_id} 时连接超时，重试 {attempt + 1}/{retries}")
            await asyncio.sleep(delay)  # 延迟后重试
        except Exception as e:
            app.logger.error(f"获取订单 {yuyue_id} 时出错：{e}")
            await asyncio.sleep(delay)  # 延迟后重试
    return None  # 在多次重试失败后返回 None

# 插入新订单到数据库
def insert_new_orders(app, orders):
    try:
        for order_data in orders:
            # 检查数据库中是否已经存在相同的 yuyue_id
            existing_order = Order.query.filter_by(yuyue_id=order_data['yuyue_id']).first()
            if not existing_order:
                # 如果订单不存在，创建新的 Order 对象并添加到数据库
                order = Order(
                    yuyue_id=order_data['yuyue_id'],
                    venue=order_data['venue'],
                    name=order_data['name'],
                    phone=order_data['phone'],
                    date=order_data['date'],
                    time=order_data['time']
                )
                db.session.add(order)
        db.session.commit()  # 提交所有订单
        app.logger.info(f"新增订单数量: {len(orders)}")
    except SQLAlchemyError as e:
        db.session.rollback()  # 出现错误时回滚
        app.logger.error(f"插入新订单时数据库错误：{e}")

# 检查数据库中现有订单的状态
def check_existing_orders(app):
    yuyue_ids = [order.yuyue_id for order in Order.query.all()]
    
    # 异步检查订单状态
    async def check_orders(ids):
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            tasks = []
            for yuyue_id in ids:
                url = f"http://cgyytyb.cpu.edu.cn/wap/yuyueIn?id={yuyue_id}"
                tasks.append(check_order_status(app, session, yuyue_id, url))
            await asyncio.gather(*tasks)

    # 检查单个订单状态
    async def check_order_status(app, session, yuyue_id, url):
        try:
            async with session.get(url, headers=app.config['HEADERS']) as response:
                content = await response.text()
                if '订单已取消，禁止进场' in content:
                    # 从数据库中删除该订单
                    order = Order.query.filter_by(yuyue_id=yuyue_id).first()
                    if order:
                        db.session.delete(order)
                        db.session.commit()
                    app.logger.info(f"订单 {yuyue_id} 已取消，已从数据库中移除")
        except Exception as e:
            app.logger.error(f"检查订单 {yuyue_id} 状态时发生错误: {e}")

    asyncio.run(check_orders(yuyue_ids))

# 提取订单信息的函数
def extract_order_info(app, yuyue_id, content):
    soup = BeautifulSoup(content, 'html.parser')
    order_data = {}
    try:
        if '审核通过，可以进场' in content:
            # 找到预约场馆
            venue_label = soup.find('label', string='预约场馆')
            if not venue_label:
                app.logger.error(f"无法找到预约场馆标签，yuyue_id={yuyue_id}")
                return None
            venue = venue_label.find_next_sibling('div').text.strip()

            # 找到预约姓名和电话
            name_hp_div = soup.find('label', string='预约姓名').find_next_sibling('div')
            if not name_hp_div:
                app.logger.error(f"无法找到预约姓名标签，yuyue_id={yuyue_id}")
                return None
            name = name_hp_div.contents[0].strip()
            phone = name_hp_div.find('span').text.strip() if name_hp_div.find('span') else ''

            # 找到预约时间
            date_time_div = soup.find('label', string='预约时间').parent
            date_span = date_time_div.find('span', style='font-weight:600;margin-right:1rem')
            date = date_span.text.strip() if date_span else ''

            time_em = date_time_div.find('em')
            time_info = time_em.text.strip() if time_em else ''

            # 组装订单信息字典
            order_data = {
                'yuyue_id': yuyue_id,
                'venue': venue,
                'name': name,
                'phone': phone,
                'date': date,
                'time': time_info
            }
            app.logger.info(f"提取订单 {yuyue_id} 成功")
        else:
            # 订单未审核通过或其他状态
            app.logger.info(f"订单 {yuyue_id} 状态不符")
            return None
    except Exception as e:
        app.logger.error(f"提取订单 {yuyue_id} 时出错：{e}")
        return None

    return order_data
