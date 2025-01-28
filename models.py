from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

# 简化数据库初始化
db = SQLAlchemy(model_class=Base)

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), nullable=False, default='user')  # 'admin', 'user', 'viewer'
    created_at = db.Column(db.DateTime, default=datetime.now)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    specification = db.Column(db.String(100))
    quantity = db.Column(db.Integer, default=0)
    min_quantity = db.Column(db.Integer, default=0)  # 安全库存阈值
    supplier = db.Column(db.String(100))  # 供应商
    price = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
    
    stock_records = db.relationship('StockRecord', backref='product', lazy=True,
                                  cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Product {self.name}>'

class StockRecord(db.Model):
    __tablename__ = 'stock_records'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.String(50), db.ForeignKey('products.product_id'), nullable=False)
    operation_type = db.Column(db.String(20), nullable=False)  # 'in', 'out', 'adjust'
    destination = db.Column(db.String(50))  # 添加出库去向字段
    supplier = db.Column(db.String(100))  # 添加供应商字段
    quantity = db.Column(db.Integer, nullable=False)
    operator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now)
    
    operator = db.relationship('User', backref='stock_records')

    def __repr__(self):
        return f'<StockRecord {self.operation_type} {self.quantity}>' 