# yourapplication/forms.py

from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, SelectField, DateField, SubmitField
from wtforms.validators import DataRequired, Length, Regexp, NumberRange, Optional
from config import Config

class ReservationForm(FlaskForm):
    yuyue_name = StringField('姓名（留空则随机生成）：', validators=[
        Optional(),
        Length(max=50, message="姓名长度不能超过50个字符")
    ])
    yuyue_hp = StringField('联系电话（留空则随机生成）：', validators=[
        Optional(),
        Length(max=20, message="电话长度不能超过20个字符"),
        Regexp(r'^\d{11}$', message="请输入有效的11位电话号码")
    ])
    yuyue_time = IntegerField('开始时间（例如：19）：', validators=[
        DataRequired(message="开始时间不能为空"),
        NumberRange(min=0, max=23, message="时间必须在0到23之间")
    ])
    yuyue_riqi = DateField('预约日期：', validators=[DataRequired(message="日期不能为空")])
    yuyue_changguan = SelectField('场馆选择：', choices=[
        (key, value) for key, value in Config.CHANGGUAN_OPTIONS.items()
    ], coerce=int, validators=[DataRequired(message="请选择场馆")])
    submit = SubmitField('提交预约')
