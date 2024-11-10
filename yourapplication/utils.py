# yourapplication/utils.py

import asyncio
import aiohttp
import random
from bs4 import BeautifulSoup
from flask import current_app
from yourapplication.models import db, Order
from sqlalchemy.exc import SQLAlchemyError

# 更新数据库的函数，根据用户指定的 yuyue_id 范围
def update_database_with_range(start_id, end_id):
    app = current_app
    app.logger.info(f"开始更新数据库，范围：{start_id} - {end_id}")

    # 异步获取新的订单数据
    new_orders = asyncio.run(fetch_new_orders(start_id, end_id))

    # 清空原有的订单数据
    delete_all_orders()

    # 插入新的订单到数据库
    insert_new_orders(new_orders)

    app.logger.info("数据库更新完成")

# 删除所有订单
def delete_all_orders():
    app = current_app
    try:
        num_deleted = db.session.query(Order).delete()
        db.session.commit()
        app.logger.info(f"已删除 {num_deleted} 条订单记录")
    except SQLAlchemyError as e:
        db.session.rollback()
        app.logger.error(f"删除所有订单时数据库错误：{e}")

# 异步获取新订单数据
async def fetch_new_orders(start_id, end_id):
    app = current_app
    app.logger.info(f"开始获取新订单，范围：{start_id} - {end_id}")
    tasks = []
    headers = app.config['HEADERS']
    async with aiohttp.ClientSession() as session:
        # 创建获取每个订单的任务列表
        for yuyue_id in range(start_id, end_id + 1):
            tasks.append(fetch_order(session, yuyue_id, headers))
        results = await asyncio.gather(*tasks)
    return [result for result in results if result]  # 过滤掉 None 的结果

# 异步获取单个订单的函数，带重试机制和随机延迟
async def fetch_order(session, yuyue_id, headers, retries=5):
    app = current_app
    url = f"https://cgyytyb.cpu.edu.cn/wap/yuyueIn?id={yuyue_id}"
    for attempt in range(retries):
        try:
            # 发起 GET 请求获取订单内容
            async with session.get(url, headers=headers, timeout=20) as response:
                content = await response.text()
                order_data = extract_order_info(yuyue_id, content)
                # 随机延迟，防止反爬
                await asyncio.sleep(random.uniform(0.5, 1.5))
                return order_data
        except asyncio.TimeoutError:
            app.logger.error(f"获取订单 {yuyue_id} 时连接超时，重试 {attempt + 1}/{retries}")
            await asyncio.sleep(random.uniform(1, 2))  # 延迟后重试
        except Exception as e:
            app.logger.error(f"获取订单 {yuyue_id} 时出错：{e}")
            await asyncio.sleep(random.uniform(1, 2))  # 延迟后重试
    return None  # 在多次重试失败后返回 None

# 插入新订单到数据库
def insert_new_orders(orders):
    app = current_app
    try:
        for order_data in orders:
            # 创建新的 Order 对象并添加到数据库
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
        app.logger.info(f"已插入订单数量: {len(orders)}")
    except SQLAlchemyError as e:
        db.session.rollback()  # 出现错误时回滚
        app.logger.error(f"插入新订单时数据库错误：{e}")

# 提取订单信息的函数
def extract_order_info(yuyue_id, content):
    app = current_app
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
