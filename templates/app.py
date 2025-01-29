# 构建查询
query = StockRecord.query.filter(StockRecord.operation_type != 'adjust').order_by(StockRecord.timestamp.desc())

# 应用日期筛选

summary = {
    'in_count': StockRecord.query.filter_by(operation_type='in').count(),
    'in_quantity': sum(r.quantity for r in StockRecord.query.filter_by(operation_type='in').all()),
    'out_count': StockRecord.query.filter_by(operation_type='out').count(),
    'out_quantity': sum(r.quantity for r in StockRecord.query.filter_by(operation_type='out').all())
} 