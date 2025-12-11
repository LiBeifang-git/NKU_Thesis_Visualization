# save as mysql_pymysql_example.py
import pymysql
from getpass import getpass

def main():
    host = "10.136.68.143"
    user = "root"
    password = getpass("请输入 MySQL 密码: ")
    database = "nk_thesis"  # 根据需要修改

    try:
        conn = pymysql.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            port=3306,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=5
        )
        with conn:
            with conn.cursor() as cur:
                # 示例：查看表列表
                cur.execute("SHOW TABLES;")
                tables = cur.fetchall()
                print("Tables:", tables)


    except pymysql.MySQLError as e:
        print("MySQL 错误：", e)
    except Exception as e:
        print("其他错误：", e)

if __name__ == "__main__":
    main()
