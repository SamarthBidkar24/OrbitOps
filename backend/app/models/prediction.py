from sqlalchemy import Column, Integer, String, Float, DateTime, func
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String, nullable=False)          # neo | spectra | meteor
    input_data = Column(String, nullable=False)          # JSON string of input features
    result = Column(String, nullable=True)               # JSON string of prediction output
    confidence = Column(Float, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
