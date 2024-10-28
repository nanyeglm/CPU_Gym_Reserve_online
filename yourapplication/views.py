# yourapplication/views.py

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from .forms import ReservationForm
from .models import db, Order, Reservation
from faker import Faker
import requests
import re
import json
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError

import time  # 导入 time 库

main_bp = Blueprint('main', __name__, template_folder='templates')
fake = Faker("zh_CN")

@main_bp.route('/', methods=['GET', 'POST'])
def index():
    form = ReservationForm()
    if form.validate_on_submit():
        try:
            # 获取表单数据
            yuyue_name = form.yuyue_name.data.strip() or fake.name()
            yuyue_hp = form.yuyue_hp.data.strip() or fake.phone_number()
            yuyue_time = str(form.yuyue_time.data)
            yuyue_riqi = form.yuyue_riqi.data.strftime('%Y-%m-%d')
            yuyue_changguan = form.yuyue_changguan.data

            # 根据姓名获取对应的 openid
            yuyue_openid = current_app.config['NAME_OPENID_MAP'].get(yuyue_name, current_app.config['DEFAULT_OPENID'])

            # 获取 yyp_pass，使用重试机制
            pass_url = f"http://cgyytyb.cpu.edu.cn/wap/yuyue?id={yuyue_changguan}"
            retries = 5
            delay = 0.2
            yyp_pass = None
            for attempt in range(retries):
                try:
                    response = requests.get(pass_url, headers=current_app.config['HEADERS'], timeout=10)
                    response.raise_for_status()
                    yyp_pass = extract_yyp_pass(response.text)
                    if yyp_pass:
                        break  # 成功获取到 yyp_pass，跳出循环
                    else:
                        current_app.logger.warning(f"获取 yyp_pass 失败, 重试 {attempt + 1}/{retries}")
                except requests.RequestException as e:
                    current_app.logger.error(f"获取 yyp_pass 请求出错: {e}")
                time.sleep(delay)  # 等待指定时间后再重试

            if not yyp_pass:
                flash("无法获取预约密钥，请稍后再试。", "danger")
                return redirect(url_for('main.index'))

            # 构建预约数据
            data = {
                'isWeb': 1,
                'API': 'saveYuyue',
                'noSave': 'yuyue_id',
                'back': 'yuyue_id',
                'yyp_pass': yyp_pass,
                'yuyue_riqi': yuyue_riqi,
                'yuyue_time': yuyue_time,
                'yuyue_name': yuyue_name,
                'yuyue_hp': yuyue_hp,
                'yuyue_view': -1,
                'yuyue_changguan': yuyue_changguan,
                'yuyue_openid': yuyue_openid,
                'yuyue_chengren': 1
            }

            # 发送预约请求
            reserve_url = "http://cgyytyb.cpu.edu.cn/inc/ajax/save/saveYuyue"
            try:
                response = requests.post(reserve_url, headers=current_app.config['HEADERS'], data=data, timeout=10)
                response.raise_for_status()
            except requests.RequestException as e:
                current_app.logger.error(f"发送预约请求时出错：{e}")
                flash("发送预约请求失败，请稍后再试。", "danger")
                return redirect(url_for('main.index'))

            try:
                json_data = response.json()
                server_response = json.dumps(json_data, ensure_ascii=False, indent=4)
                yuyue_id = int(json_data['data']['yuyue_id'])
            except (ValueError, KeyError) as e:
                current_app.logger.error(f"解析服务器响应时出错：{e}")
                server_response = response.text
                flash("预约失败，无法解析服务器响应。", "danger")
                return redirect(url_for('main.index'))

            # 保存预约到数据库
            reservation = Reservation(
                yuyue_id=yuyue_id,
                venue=current_app.config['CHANGGUAN_OPTIONS'].get(yuyue_changguan, "未知场馆"),
                name=yuyue_name,
                phone=yuyue_hp,
                date=yuyue_riqi,
                time=yuyue_time
            )
            try:
                db.session.add(reservation)
                db.session.commit()
                current_app.logger.info(f"保存预约 {yuyue_id}")
            except SQLAlchemyError as e:
                db.session.rollback()
                current_app.logger.error(f"保存预约 {yuyue_id} 时出错：{e}")
                flash("保存预约信息失败，请稍后再试。", "danger")
                return redirect(url_for('main.index'))

            return render_template('result.html',
                                   yuyue_name=yuyue_name,
                                   yuyue_time=yuyue_time,
                                   yuyue_hp=yuyue_hp,
                                   yuyue_changguan=current_app.config['CHANGGUAN_OPTIONS'].get(yuyue_changguan, "未知场馆"),
                                   yuyue_riqi=yuyue_riqi,
                                   server_response=server_response)
        except Exception as e:
            current_app.logger.error(f"发生错误: {str(e)}")
            flash(f"发生错误: {str(e)}", "danger")
            return redirect(url_for('main.index'))
    else:
        # GET 请求或表单验证失败
        if request.method == 'POST' and form.errors:
            for field_errors in form.errors.values():
                for error in field_errors:
                    flash(error, "danger")
    return render_template('index.html', form=form)

# 提取 yyp_pass 的辅助函数
def extract_yyp_pass(content):
    patterns = [
        r"post\.yyp_pass=['\"](.*?)['\"]",
        r"yyp_pass\s*=\s*['\"](.*?)['\"]",
        r"name=['\"]yyp_pass['\"]\s*value=['\"](.*?)['\"]",
    ]
    for pattern in patterns:
        match = re.search(pattern, content)
        if match:
            return match.group(1)
    return None

@main_bp.route('/orders')
def view_orders():
    # 定义场馆分组
    venue_groups = {
        '体育馆三楼羽毛球馆': [
            '体育馆三楼羽毛球馆1号场',
            '体育馆三楼羽毛球馆2号场',
            '体育馆三楼羽毛球馆3号场',
            '体育馆三楼羽毛球馆4号场',
            '体育馆三楼羽毛球馆5号场',
            '体育馆三楼羽毛球馆6号场',
            '体育馆三楼羽毛球馆7号场'
        ],
        '体育馆一楼羽毛球馆': [
            '体育馆一楼羽毛球馆1号场',
            '体育馆一楼羽毛球馆2号场',
            '体育馆一楼羽毛球馆3号场',
            '体育馆一楼羽毛球馆4号场',
            '体育馆一楼羽毛球馆5号场',
            '体育馆一楼羽毛球馆6号场'
        ],
        '教室': [
            '体育馆一楼教室一',
            '体育馆一楼教室二',
            '体育馆一楼教室三',
            '体育馆四楼教室四',
            '体育场形体房',
            '体育场跆拳道房'
        ],
        '田径场健身房': [
            '田径场健身房'
        ]
    }

    # 建立实际场馆到分组场馆的映射
    venue_mapping = {}
    for group_name, venues in venue_groups.items():
        for v in venues:
            venue_mapping[v] = group_name

    selected_group = request.args.get('venue_group', '')
    selected_venue = request.args.get('venue', '')
    selected_date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    selected_time = request.args.get('time', '')

    # 根据选择的场馆分组获取具体场馆
    if selected_group and selected_group in venue_groups:
        if selected_venue:
            selected_venues = [selected_venue]
        else:
            selected_venues = venue_groups[selected_group]
    else:
        selected_venues = None  # 表示不进行场馆筛选

    # 查询订单
    query = Order.query
    if selected_venues:
        query = query.filter(Order.venue.in_(selected_venues))
    if selected_date:
        query = query.filter(Order.date == selected_date)
    if selected_time:
        query = query.filter(Order.time.like(f"%{selected_time}%"))

    orders = query.order_by(Order.venue, Order.time).all()

    # 查询预约
    reservations_query = Reservation.query.filter_by(date=selected_date)
    if selected_venues:
        reservations_query = reservations_query.filter(Reservation.venue.in_(selected_venues))
    if selected_time:
        reservations_query = reservations_query.filter(Reservation.time.like(f"%{selected_time}%"))

    reservations = reservations_query.order_by(Reservation.venue, Reservation.time).all()

    # 获取所有场馆分组名称，供筛选使用
    all_venue_groups = list(venue_groups.keys())

    # 处理订单数据，拆分时间段
    processed_orders = []
    for order in orders:
        yuyue_id = order.yuyue_id
        venue = order.venue
        grouped_venue = venue_mapping.get(venue, venue)
        times = [t.strip() for t in order.time.split(';') if t.strip()]
        for time in times:
            # 如果有时间筛选，检查是否匹配
            if selected_time and selected_time not in time:
                continue
            processed_orders.append({
                'yuyue_id': yuyue_id,
                'venue': venue,
                'grouped_venue': grouped_venue,
                'name': order.name,
                'phone': order.phone,
                'date': order.date,
                'time': time
            })

    # 定义排序键函数
    venue_order = [
        '体育馆三楼羽毛球馆1号场',
        '体育馆三楼羽毛球馆2号场',
        '体育馆三楼羽毛球馆3号场',
        '体育馆三楼羽毛球馆4号场',
        '体育馆三楼羽毛球馆5号场',
        '体育馆三楼羽毛球馆6号场',
        '体育馆三楼羽毛球馆7号场',
        '体育馆一楼羽毛球馆1号场',
        '体育馆一楼羽毛球馆2号场',
        '体育馆一楼羽毛球馆3号场',
        '体育馆一楼羽毛球馆4号场',
        '体育馆一楼羽毛球馆5号场',
        '体育馆一楼羽毛球馆6号场',
        '体育馆一楼教室一',
        '体育馆一楼教室二',
        '体育馆一楼教室三',
        '体育馆四楼教室四',
        '体育场形体房',
        '体育场跆拳道房',
        '田径场健身房',
        # 其他场馆可以按需添加
    ]
    venue_order_index = {venue: index for index, venue in enumerate(venue_order)}

    def sorting_key(order):
        venue_index = venue_order_index.get(order['venue'], 9999)  # 未知场馆放在最后
        try:
            hour = int(order['time'].split(':')[0])
        except:
            hour = 9999
        return (venue_index, hour)

    # 按照指定顺序排序
    processed_orders.sort(key=sorting_key)

    # 处理预约记录
    processed_reservations = []
    for res in reservations:
        grouped_venue = venue_mapping.get(res.venue, res.venue)
        processed_reservations.append({
            'yuyue_id': res.yuyue_id,
            'venue': res.venue,
            'grouped_venue': grouped_venue,
            'name': res.name,
            'phone': res.phone,
            'date': res.date,
            'time': res.time
        })

    # 对预约记录进行排序
    processed_reservations.sort(key=sorting_key)

    return render_template('orders.html',
                           orders=processed_orders,
                           reservations=processed_reservations,
                           selected_group=selected_group,
                           selected_venue=selected_venue,
                           selected_date=selected_date,
                           selected_time=selected_time,
                           all_venue_groups=all_venue_groups,
                           venue_groups=venue_groups)

@main_bp.route('/cancel_order/<int:yuyue_id>', methods=['POST'])
def cancel_order(yuyue_id):
    try:
        # 取消订单的请求 URL
        cancel_url = "http://cgyytyb.cpu.edu.cn/inc/ajax/save/tuikuan"

        # 取消订单的数据
        data = {
            'isWeb': 1,
            'tuikuan_id': yuyue_id,  # 退款ID，即 yuyue_id
            'API': 'tuikuan',
            'tuikuanflag': 'yuyue'
        }

        # 发送取消订单的 POST 请求
        response = requests.post(cancel_url, headers=current_app.config['HEADERS'], data=data, timeout=10)
        response.raise_for_status()

        # 解析响应
        json_data = response.json()
        if json_data.get('Code') == '0':
            # 取消成功，删除订单和相关预约
            order = Order.query.filter_by(yuyue_id=yuyue_id).first()
            if order:
                db.session.delete(order)
            reservation = Reservation.query.filter_by(yuyue_id=yuyue_id).first()
            if reservation:
                db.session.delete(reservation)
            db.session.commit()
            flash("订单已成功取消。", "success")
            current_app.logger.info(f"取消订单 {yuyue_id}")
        else:
            # 取消失败
            msg = json_data.get('Msg', '取消订单失败。')
            flash(f"取消订单失败：{msg}", "danger")
            current_app.logger.error(f"取消订单 {yuyue_id} 失败：{msg}")
    except requests.RequestException as e:
        current_app.logger.error(f"发送取消请求时出错：{e}")
        flash("取消订单请求失败，请稍后再试。", "danger")
    except (ValueError, KeyError):
        # 解析失败
        flash("取消订单时无法解析服务器响应。", "danger")
        current_app.logger.error(f"取消订单 {yuyue_id} 时解析响应失败。")
    except SQLAlchemyError as e:
        db.session.rollback()
        flash("取消订单时数据库错误。", "danger")
        current_app.logger.error(f"取消订单 {yuyue_id} 时数据库错误：{e}")

    return redirect(url_for('main.view_orders'))

