from . import db, app
from flask_login import UserMixin
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String, LargeBinary, Float, CheckConstraint

class Users(db.Model, UserMixin):
    
    # Creating the table Users.
    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(15), unique=True, nullable=False)
    last_name: Mapped[str] = mapped_column(String(15), nullable=False)
    password: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    role: Mapped[str] = mapped_column(String(15), nullable=False)

    # Returns info.
    def __repr__(self):
        return f"User {self.first_name, self.last_name}"
    
class Products(db.Model):
    
    # Creating the table Products.
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    minimum_quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    # Adding Constraints.
    __table_args__ = (
        CheckConstraint(price > 0, name = 'price_check'), 
        CheckConstraint(quantity >= 0, name = 'quantity_check'), 
        CheckConstraint(minimum_quantity >= 0, name = 'min_quantity_check'))
    
with app.app_context():
    db.create_all()