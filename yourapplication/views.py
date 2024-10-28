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

main_bp = Blueprint('main', __name__)
fake = Faker("zh_CN")

@main_bp.route('/', methods=['GET', 'POST'])
def index():
    form = ReservationForm()
    if form.validate_on_submit():
        yuyue_name = form.yuyue_name.data.strip() or fake.name()
        yuyue_hp = form.yuyue_hp.data.strip() or fake.phone_number()
        yuyue_time = str(form.yuyue_time.data)
        yuyue_riqi = form.yuyue_riqi.data.strftime('%Y-%m-%d')
        yuyue_changguan = form.yuyue_changguan.data

        yuyue_openid = current_app.config['NAME_OPENID_MAP'].get(yuyue_name, current_app.config['DEFAULT_OPENID'])

        # 获取 yyp_pass
        pass_url = f"http://cgyytyb.cpu.edu.cn/wap/yuyue?id={yuyue_changguan}"
        pass_response = requests.get(pass_url, headers=current_app.config['HEADERS'])
        pass_page_content = pass_response.text

        yyp_pass = extract_yyp_pass(pass_page_content)
        if not yyp_pass:
            flash("未能获取 yyp_pass，无法预约", "danger")
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
        response = requests.post(reserve_url, headers=current_app.config['HEADERS'], data=data)

        try:
            json_data = response.json()
            server_response = json.dumps(json_data, ensure_ascii=False, indent=4)
            yuyue_id = int(json_data['data']['yuyue_id'])

            # 保存预约到数据库
            reservation = Reservation(
                yuyue_id=yuyue_id,
                venue=current_app.config['CHANGGUAN_OPTIONS'].get(yuyue_changguan, "未知场馆"),
                name=yuyue_name,
                phone=yuyue_hp,
                date=yuyue_riqi,
                time=yuyue_time
            )
            db.session.add(reservation)
            db.session.commit()
            current_app.logger.info(f"保存预约 {yuyue_id}")
        except (ValueError, KeyError, SQLAlchemyError) as e:
            db.session.rollback()
            server_response = response.text
            current_app.logger.error(f"处理预约时出错：{e}")
            flash("预约失败，请检查输入信息或稍后再试", "danger")
            return redirect(url_for('main.index'))

        return render_template('result.html',
                               yuyue_name=yuyue_name,
                               yuyue_time=yuyue_time,
                               yuyue_hp=yuyue_hp,
                               yuyue_changguan=current_app.config['CHANGGUAN_OPTIONS'].get(yuyue_changguan, "未知场馆"),
                               yuyue_riqi=yuyue_riqi,
                               server_response=server_response)
    else:
        if form.errors:
            for field_errors in form.errors.values():
                for error in field_errors:
                    flash(error, "danger")
        return render_template('index.html', form=form)

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
    selected_venue = request.args.get('venue', '体育馆三楼羽毛球馆')
    selected_date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    selected_time = request.args.get('time', '')

    # 查询订单
    query = Order.query
    if selected_venue:
        query = query.filter(Order.venue.contains(selected_venue))
    if selected_date:
        query = query.filter(Order.date == selected_date)
    if selected_time:
        query = query.filter(Order.time.contains(selected_time))

    orders = query.order_by(Order.venue, Order.time).all()

    # 查询预约
    res_query = Reservation.query.filter_by(date=selected_date)
    reservations = res_query.order_by(Reservation.venue, Reservation.time).all()

    all_venues = list(set(order.venue for order in orders))

    return render_template('orders.html',
                           orders=orders,
                           reservations=reservations,
                           selected_venue=selected_venue,
                           selected_date=selected_date,
                           selected_time=selected_time,
                           all_venues=all_venues)

@main_bp.route('/cancel_order/<int:yuyue_id>', methods=['POST'])
def cancel_order(yuyue_id):
    # 取消订单逻辑
    cancel_url = "http://cgyytyb.cpu.edu.cn/inc/ajax/save/tuikuan"
    data = {
        'isWeb': 1,
        'tuikuan_id': yuyue_id,
        'API': 'tuikuan',
        'tuikuanflag': 'yuyue'
    }
    response = requests.post(cancel_url, headers=current_app.config['HEADERS'], data=data)

    try:
        json_data = response.json()
        if json_data.get('Code') == '0':
            # 删除数据库中的订单
            Order.query.filter_by(yuyue_id=yuyue_id).delete()
            Reservation.query.filter_by(yuyue_id=yuyue_id).delete()
            db.session.commit()
            flash("订单已成功取消。", "success")
        else:
            msg = json_data.get('Msg', '取消订单失败。')
            flash(f"取消订单失败：{msg}", "danger")
    except ValueError:
        flash("取消订单失败，无法解析服务器响应。", "danger")

    return redirect(url_for('main.view_orders'))
