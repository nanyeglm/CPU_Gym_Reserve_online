# yourapplication/models.py

from . import db

class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    yuyue_id = db.Column(db.Integer, unique=True, nullable=False, index=True)
    venue = db.Column(db.String(100), index=True)
    name = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    date = db.Column(db.String(20), index=True)
    time = db.Column(db.String(20), index=True)

    def __repr__(self):
        return f"<Order {self.yuyue_id}>"

class Reservation(db.Model):
    __tablename__ = 'reservations'
    id = db.Column(db.Integer, primary_key=True)
    yuyue_id = db.Column(db.Integer, index=True)
    venue = db.Column(db.String(100), index=True)
    name = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    date = db.Column(db.String(20), index=True)
    time = db.Column(db.String(20), index=True)

    def __repr__(self):
        return f"<Reservation {self.yuyue_id}>"
