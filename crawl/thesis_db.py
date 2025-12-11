import pymysql

class ThesisDB:
    def __init__(self, host="localhost", user="root", password="cjy20030306yuE", database="nk_thesis"):
        self.db = pymysql.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            charset="utf8mb4"
        )
        self.cursor = self.db.cursor()
        # 定义 SQL 模板（只初始化一次）
        self.sql = """
        INSERT INTO thesis_detail (
            id, 点击量, url,中文标题,
            语种, 学科代码, 学科名称, 学生类型, 学位, 保密级别, 学号, 作者, 培养单位,
            院系, 系所, 专业, 研究方向, 第一导师姓名, 第一导师单位, 论文终稿完成日期, 答辩日期,
            学位年度, 外文题名, 中文关键词, 外文关键词, 中文摘要, 外文摘要,
            参考文献总数, 开放日期
        ) VALUES (
            %(id)s, %(点击量)s, %(url)s,%(中文标题)s,
            %(语种：)s, %(学科代码：)s, %(学科名称：)s, %(学生类型：)s, %(学位：)s, %(保密级别：)s,
            %(学号：)s, %(作者：)s, %(培养单位：)s, %(院系：)s, %(系所：)s, %(专业：)s, %(研究方向：)s,
            %(第一导师姓名：)s, %(第一导师单位：)s, %(论文终稿完成日期：)s, %(答辩日期：)s,
            %(学位年度：)s, %(外文题名：)s, %(中文关键词：)s, %(外文关键词：)s,
            %(中文摘要：)s, %(外文摘要：)s,
            %(参考文献总数：)s, %(开放日期：)s
        )
        """

    def insert_detail(self, detail_data: dict):
        """插入单条论文详情数据"""
        try:
            self.cursor.execute(self.sql, detail_data)
            self.db.commit()
            print(f"✅ 插入成功：id={detail_data.get('id')}")
        except Exception as e:
            print("❌ 插入失败：", e)
            self.db.rollback()

    def close(self):
        self.cursor.close()
        self.db.close()
    
    def update_title(self, thesis_id, title_cn, thesis_author, mentor, degree, year):
        """更新指定论文的中文标题"""
        try:
            sql = """
                UPDATE thesis_detail
                SET 中文标题 = %s
                WHERE 作者 = %s
                AND 第一导师姓名 = %s
                AND 学位 = %s
                AND 学位年度 = %s
            """
            self.cursor.execute(sql, (title_cn, thesis_author, mentor, degree, year))
            self.db.commit()
            print("更新成功！！")
            return self.cursor.rowcount
        except Exception as e:
            self.db.rollback()
            print(f"更新标题失败: {e}")
            return 0

