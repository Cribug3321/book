import pymysql

# 添加这一行，手动把伪装版本号改成 Django 期望的 2.2.1 或更高
pymysql.version_info = (2, 2, 1, 'final', 0)

pymysql.install_as_MySQLdb()