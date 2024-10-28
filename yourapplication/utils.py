# yourapplication/utils.py

import asyncio
import aiohttp
import time
import logging
from bs4 import BeautifulSoup
from threading import Thread
from flask import current_app
from yourapplication.models import db, Order
from sqlalchemy.exc import SQLAlchemyError

def start_background_tasks(app):
    def run_update():
        with app.app_context():
            while True:
                try:
                    update_database()
                except Exception as e:
                    app.logger.error(f"后台更新任务出错：{e}")
                time.sleep(180)  # 每隔3分钟运行一次

    thread = Thread(target=run_update)
    thread.daemon = True
    thread.start()

def update_database():
    app = current_app._get_current_object()
    app.logger.info("开始更新数据库")
    # 获取最新的 yuyue_id
    max_yuyue_id = db.session.query(db.func.max(Order.yuyue_id)).scalar() or 823
    new_orders = asyncio.run(fetch_new_orders(max_yuyue_id + 1, max_yuyue_id + 200))

    for order_data in new_orders:
        if order_data:
            order = Order(
                yuyue_id=order_data['yuyue_id'],
                venue=order_data['venue'],
                name=order_data['name'],
                phone=order_data['phone'],
                date=order_data['date'],
                time=order_data['time']
            )
            try:
                db.session.add(order)
                db.session.commit()
                app.logger.info(f"添加新订单 {order_data['yuyue_id']}")
            except SQLAlchemyError as e:
                db.session.rollback()
                app.logger.error(f"数据库错误：{e}")

    app.logger.info("数据库更新完成")

async def fetch_new_orders(start_id, end_id):
    tasks = []
    async with aiohttp.ClientSession() as session:
        for yuyue_id in range(start_id, end_id):
            tasks.append(fetch_order(session, yuyue_id))
        results = await asyncio.gather(*tasks)
    return results

async def fetch_order(session, yuyue_id):
    url = f"http://cgyytyb.cpu.edu.cn/wap/yuyueIn?id={yuyue_id}"
    headers = current_app.config['HEADERS']
    try:
        async with session.get(url, headers=headers) as response:
            content = await response.text()
            order_data = extract_order_info(yuyue_id, content)
            await asyncio.sleep(0.1)
            return order_data
    except Exception as e:
        current_app.logger.error(f"获取订单 {yuyue_id} 时出错：{e}")
        return None

def extract_order_info(yuyue_id, content):
    soup = BeautifulSoup(content, 'html.parser')
    order_data = {}
    try:
        if '审核通过，可以进场' in content:
            venue_label = soup.find('label', string='预约场馆')
            venue = venue_label.find_next_sibling('div').text.strip()

            name_hp_div = soup.find('label', string='预约姓名').find_next_sibling('div')
            name = name_hp_div.contents[0].strip()
            phone = name_hp_div.find('span').text.strip()

            date_time_div = soup.find('label', string='预约时间').parent
            date = date_time_div.find('span', style='font-weight:600;margin-right:1rem').text.strip()
            time_info = date_time_div.find('em').text.strip()

            order_data = {
                'yuyue_id': yuyue_id,
                'venue': venue,
                'name': name,
                'phone': phone,
                'date': date,
                'time': time_info
            }
            current_app.logger.info(f"提取订单 {yuyue_id} 成功")
        else:
            return None
    except Exception as e:
        current_app.logger.error(f"提取订单 {yuyue_id} 时出错：{e}")
        return None

    return order_data
