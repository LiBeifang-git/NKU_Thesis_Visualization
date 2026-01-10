from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from thesis_db import ThesisDB
import time
import csv
# 你的 geckodriver 路径
service = Service(r"E:\geckodriver.exe")
options = webdriver.FirefoxOptions()
# 不要 headless，否则你看不到登录界面
driver = webdriver.Firefox(service=service, options=options)
db = ThesisDB()

def login():
    # 1. 打开登录页面
    driver.get("https://thesis.nankai.edu.cn/login")
    print("已打开登录页")
    time.sleep(2)
    # 2. 点击 “立即进行统一认证登录” 按钮
    try:
        btn = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(text(),'立即进行统一认证登录')]"))
        )
        btn.click()
        print("已点击统一认证登录按钮")
    except Exception as e:
        print(f"❌ 按钮没找到，请检查页面是否更新：{e}")
    # 3. 等待 CAS 登录页面加载
    try:
        # 等待学号输入框出现
        account_input = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "password_account_input"))
        )
        print("学号输入框已加载")
        
        # 输入学号
        account_input.send_keys("2113881")  # 替换成你的学号
        
        # 等待密码输入框出现
        password_input = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "password_password_input"))
        )
        print("密码输入框已加载")
        
        # 输入密码
        password_input.send_keys("cjy20030306yuE!")  # 替换成你的密码
        
        # 找到并点击登录按钮
        login_button = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@type='submit']"))
        )
        login_button.click()
        print("已点击登录按钮")
    except Exception as e:
        print(f"❌ 登录过程出错：{e}")

    # 4. 等待登录完成并检查登录状态
    print("请等待登录完成...")
    time.sleep(10)

    try:
        click_ranking_link = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(text(),'点击排行')]"))
        )
        click_ranking_link.click()
        print("已点击点击排行链接")
    except Exception as e:
        print(f"❌ 找不到点击排行链接：{e}")


def crawl_chinese_title(start=1,end=1):
    TOTAL_PAGES = end   # ← 你要求的固定页数
    if start!=1:
        input_box = driver.find_element(By.CSS_SELECTOR, "input.el-input__inner[type='number']")
        input_box.clear()
        input_box.send_keys(str(start))  # 替换成你想输入的数字
        input_box.send_keys(Keys.ENTER)
        time.sleep(2)  # 或用 WebDriverWait 等待页面元素加载

    for page in range(start, TOTAL_PAGES + 1):
        print(f"\n======================")
        print(f"开始处理第 {page} 页数据")
        print("======================\n")
        time.sleep(2)
        # 获取本页所有行
        rows = driver.find_elements(By.CSS_SELECTOR, "tr.el-table__row")
        total = len(rows)
        print("本页找到行数：", total)

        # 如果这一页空了（渲染失败）→ 刷新一次
        if total == 0:
            print("⚠ 本页行数为0，刷新重试")
            driver.refresh()
            time.sleep(2)
            rows = driver.find_elements(By.CSS_SELECTOR, "tr.el-table__row")
            total = len(rows)
            print("刷新后行数：", total)

        # -------------------------
        # 遍历本页所有行
        # -------------------------
        for i in range(1, total + 1):
            detail_data = {}
            print(f"\n------ 正在处理第 {i} 行 ------")

            # 避免 stale：重新定位
            xpath = f"(//tr[contains(@class,'el-table__row')])[{i}]"
            row = driver.find_element(By.XPATH, xpath)
            cols = row.find_elements(By.TAG_NAME, "td")

            # 列表字段
            rank = cols[0].text
            title = cols[1].find_element(By.CSS_SELECTOR, "span.el-link--inner").text
            author = cols[2].text
            mentor = cols[3].text
            degree = cols[4].text
            year = cols[5].text
            clicks = cols[6].text
            # 取出点击量
            detail_data["id"] = int(rank)
            detail_data["点击量"] = int(clicks)
            db.update_title(rank,title,author,mentor,degree,year)
            print(rank, title, author, mentor, degree, year, clicks)

        
        # ⭐ 点击下一页
        # -------------------------
        print(f"→ 正在进入第 {page+1} 页")

        try:
            next_btn = driver.find_element(By.CSS_SELECTOR, "button.btn-next")
            driver.execute_script("arguments[0].click();", next_btn)
        except Exception as e:
            print(f"❌ 翻页失败：{e}")
            print("⚠ 自动刷新并重试翻页")
            driver.refresh()
            time.sleep(2)
            try:
                next_btn = driver.find_element(By.CSS_SELECTOR, "button.btn-next")
                driver.execute_script("arguments[0].click();", next_btn)
            except:
                print("🚨 连续翻页失败，退出爬取")
                break

        time.sleep(2)

    print("所有 4460 页已完成。")

def crawl(restart=False,start=1,end=4460):
    print("开始爬取数据...")
    TOTAL_PAGES = end   # ← 你要求的固定页数
    if restart==True:
        input_box = driver.find_element(By.CSS_SELECTOR, "input.el-input__inner[type='number']")
        input_box.clear()
        input_box.send_keys(str(start))  # 替换成你想输入的数字
        input_box.send_keys(Keys.ENTER)
        time.sleep(2)  # 或用 WebDriverWait 等待页面元素加载
    for page in range(start, TOTAL_PAGES + 1):
        print(f"\n======================")
        print(f"开始处理第 {page} 页数据")
        print("======================\n")
        time.sleep(2)
        # 获取本页所有行
        rows = driver.find_elements(By.CSS_SELECTOR, "tr.el-table__row")
        total = len(rows)
        print("本页找到行数：", total)

        # 如果这一页空了（渲染失败）→ 刷新一次
        if total == 0:
            print("⚠ 本页行数为0，刷新重试")
            driver.refresh()
            time.sleep(2)
            rows = driver.find_elements(By.CSS_SELECTOR, "tr.el-table__row")
            total = len(rows)
            print("刷新后行数：", total)

        # -------------------------
        # 遍历本页所有行
        # -------------------------
        for i in range(1, total + 1):
            detail_data = {}
            print(f"\n------ 正在处理第 {i} 行 ------")

            # 避免 stale：重新定位
            xpath = f"(//tr[contains(@class,'el-table__row')])[{i}]"
            row = driver.find_element(By.XPATH, xpath)
            cols = row.find_elements(By.TAG_NAME, "td")

            # 列表字段
            rank = cols[0].text
            title = cols[1].find_element(By.CSS_SELECTOR, "span.el-link--inner").text
            author = cols[2].text
            mentor = cols[3].text
            degree = cols[4].text
            year = cols[5].text
            clicks = cols[6].text
            # 取出点击量
            detail_data["id"] = int(rank)
            detail_data["点击量"] = int(clicks)
            detail_data["中文标题"] = title

            print(rank, title, author, mentor, degree, year, clicks)

            # 打开详情页
            original_window = driver.current_window_handle
            link = cols[1].find_element(By.CSS_SELECTOR, "span.el-link--inner")

            driver.execute_script("arguments[0].click();", link)
            time.sleep(1)

            # 切换到新的 tab
            WebDriverWait(driver, 10).until(EC.number_of_windows_to_be(2))
            for handle in driver.window_handles:
                if handle != original_window:
                    driver.switch_to.window(handle)
                    break

            detail_url = driver.execute_script("return window.location.href;")
            print("详情页 URL：", detail_url)
            detail_data["url"] = detail_url

            # 爬详情页
            crawl_details(detail_data)

            # 关闭页面并返回
            driver.close()
            driver.switch_to.window(original_window)
        # -------------------------
        # ⭐ 点击下一页
        # -------------------------
        print(f"→ 正在进入第 {page+1} 页")

        try:
            next_btn = driver.find_element(By.CSS_SELECTOR, "button.btn-next")
            driver.execute_script("arguments[0].click();", next_btn)
        except Exception as e:
            print(f"❌ 翻页失败：{e}")
            print("⚠ 自动刷新并重试翻页")
            driver.refresh()
            time.sleep(2)
            try:
                next_btn = driver.find_element(By.CSS_SELECTOR, "button.btn-next")
                driver.execute_script("arguments[0].click();", next_btn)
            except:
                print("🚨 连续翻页失败，退出爬取")
                break

        time.sleep(2)

    print("所有 4460 页已完成。")

def crawl_details(detail_data):
    # 提取详情页内容
    time.sleep(2)
    detail_elements = driver.find_elements(By.CSS_SELECTOR, "ul.paper-detail-list li")
    for element in detail_elements:
        label = element.find_element(By.TAG_NAME, "label").text.strip()
        if label=="参考文献：": #不处理了太长了
            continue

        if label=="中文摘要："or label=="外文摘要：":
            try:
                expand_btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "div.abstract-more"))
                )
                driver.execute_script("arguments[0].click();", expand_btn)
                print("展开按钮已点击")
                time.sleep(1)  # 等待 DOM 更新
            except:
                print("⚠ 未找到展开按钮，可能该条不需要展开")
            div = element.find_element(By.CSS_SELECTOR, "div.text")
            div_text = div.text.strip()
            value = div_text
        else:
            value = element.find_element(By.CSS_SELECTOR, "div.text").text.strip()
            
        detail_data[label] = value

    db.insert_detail(detail_data)
    # 打印提取到的详情页数据
    print("详情页数据：")
    for key, value in detail_data.items():
        print(f"{key}: {value}")


if __name__ == '__main__':
    login()
    #crawl_chinese_title(int(31975/20),1600)
    #crawl(True,1752,1800)
    crawl(True,int(45409/20+1),4460)

