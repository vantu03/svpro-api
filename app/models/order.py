from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, func, Boolean
from sqlalchemy.orm import relationship
from app.database import Base
import enum

class OrderStatus(str, enum.Enum):
    pending                 = "pending"                 # Chờ xử lý
    accepted_pending        = "accepted_pending"        # Shipper đã nhận nhưng chờ xác nhận
    picking_up              = "picking_up"              # Đang lấy hàng
    in_transit              = "in_transit"              # Đang giao
    delivered               = "delivered"               # Giao thành công
    failed                  = "failed"                  # Giao thất bại
    cancelled               = "cancelled"               # Đã huỷ
    expired                 = "expired"                 # Hết hạn tìm shipper


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)

    # Người gửi
    sender_id = Column(Integer, ForeignKey("senders.id"), nullable=False)
    pickup_address = Column(String(255), nullable=False)
    note = Column(String(500), nullable=True)

    # Người nhận (snapshot)
    receiver_name = Column(String(120), nullable=False)
    receiver_phone = Column(String(20), nullable=False)
    receiver_address = Column(String(255), nullable=False)
    item_value = Column(Integer, nullable=False)

    # Phí ship (VNĐ)
    shipping_fee = Column(Integer, nullable=True)
    shipping_fee_confirmed = Column(Boolean, default=False)

    # Shipper đảm nhận
    shipper_id = Column(Integer, ForeignKey("shippers.id"), nullable=True)

    # Trạng thái đơn hàng
    status = Column(Enum(OrderStatus), default=OrderStatus.pending, nullable=False)

    create_at = Column(DateTime, server_default=func.now())
    update_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    sender = relationship("Sender", back_populates="orders")
    shipper = relationship("Shipper", back_populates="orders")

    def __repr__(self):
        return f"<Order(id={self.id}, sender_id={self.sender_id}, shipper_id={self.shipper_id}, status={self.status})>"
