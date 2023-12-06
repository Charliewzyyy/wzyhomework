import requests  # 网页内容获取
import re  # 解析数据
from lxml import etree  # 解析数据
import random
import csv


def ua():
    # 定义用户代理列表，模拟不同浏览器的用户信息
    user_agents = [
        'Mozilla/5.0 (Windows; U; Windows NT 5.1; it; rv:1.8.1.11) Gecko/20071127 Firefox/2.0.0.11',
        'Opera/9.25 (Windows NT 5.1; U; en)',
        'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; .NET CLR 1.1.4322; .NET CLR 2.0.50727)',
        'Mozilla/5.0 (compatible; Konqueror/3.5; Linux) KHTML/3.5.5 (like Gecko) (Kubuntu)',
        'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.8.0.12) Gecko/20070731 Ubuntu/dapper-security Firefox/1.5.0.12',
        'Lynx/2.8.5rel.1 libwww-FM/2.14 SSL-MM/1.4.1 GNUTLS/1.2.9',
        'Mozilla/5.0 (X11; Linux i686) AppleWebKit/535.7 (KHTML, like Gecko) Ubuntu/11.04 Chromium/16.0.912.77 Chrome/16.0.912.77 Safari/535.7',
        'Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:10.0) Gecko/20100101 Firefox/10.0',
    ]

    agent = random.choice(user_agents)  # 从用户代理列表中随机选择一个用户代理

    # 返回包含随机选择的用户代理的字典
    return {'User-Agent': agent}


def get(url):
    # 发送带有随机用户代理的请求，获取网页源码
    res = requests.get(url=url, headers=ua())
    return res.text


def get_url(res_text):
    # 使用正则表达式提取包含电影详情页URL的部分
    re_f = r'href:\'(/movie/\d+)\''

    # 使用正则表达式找到匹配的所有URL，并以列表形式返回
    url_list = re.findall(re_f, res_text)
    return url_list


def get_data(movie_text):
    movie_text = etree.HTML(movie_text)

    movie_title = movie_text.xpath('//p[@class="info-title"]/span[@class="info-title-content"]/text()')[0].strip()

    category = movie_text.xpath('//p[@class="info-category"]/text()')[0].strip()

    country = movie_text.xpath('//p[@class=".ellipsis-1"]/text()')[0].strip()  # 中国大陆\n                      /
    country = country.split('\n')[0].strip()

    date_element = movie_text.xpath('//span[@class="score-info ellipsis-1"]/text()')
    if date_element:
        date_text = date_element[0]  # 从文本中提取日期
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', date_text)  # 使用正则表达式提取日期部分
        if date_match:
            full_date = date_match.group(1)
            year, month, day = full_date.split('-')

    length = movie_text.xpath('//p[@class=".ellipsis-1"]')[0]  # <Element p at 0x207f7ccd980>
    length = length.xpath('./span/text()')[0].strip()  # 176分钟
    length = re.search(r'\d+', length).group()  # 176

    rating = movie_text.xpath('//div[@class="rating-stars"]/span[@class="rating-num"]/text()')

    rating_number = movie_text.xpath('//p[@class="detail-score-count"]')[0].text
    match = re.search(r'(\d+(\.\d+)?)万?观众评分', rating_number)
    if match:
        score_str = match.group(1)  # 提取匹配到的数字部分
        if '万' in rating_number:
            rating_number = float(score_str) * 10000
        else:
            rating_number = float(score_str)

    wishing_number = movie_text.xpath('//p[@class="detail-wish-count"]')[0].text
    match = re.search(r'(\d+(\.\d+)?)万?人想看', wishing_number)
    if match:
        score_str = match.group(1)
        if '万' in wishing_number:
            wishing_number = float(score_str) * 10000
        else:
            wishing_number = float(score_str)

    box_title = []
    boxes = []
    info_detail_row = movie_text.xpath('//div[@class="info-detail-row"]')  # 获取包含票房信息的div
    if info_detail_row:
        for col in info_detail_row[0].xpath('.//div[@class="info-detail-col"]'):
            title = col.xpath('.//p[@class="info-detail-title"]/text()')[0].strip()
            content = col.xpath('.//p[@class="info-detail-content"]')[0]
            num_match = re.search(r'(\d+\.\d+)',
                                  content.xpath('.//span[@class="detail-num"]/text()')[0])  # 使用正则表达式提取数字和单位
            unit_elements = content.xpath('.//span[@class="detail-unit"]/text()')  # 获取单位元素列表
            if num_match and unit_elements:
                num = float(num_match.group(1))
                unit = unit_elements[0]  # 取第一个单位元素
                if unit == '亿':  # 根据单位进行相应的转换
                    num *= 10000
            box_title.append(title)
            boxes.append(num)
    print(boxes)  # 反正后面要删掉预测票房，所有无所谓

    #     intro = movie_text.xpath('//div[@class="detail-block-content"]/text()')[0].strip()
    #     print(intro)

    # 返回包含上述信息的字典
    return dict(
        zip(["电影名称", "电影类型", "出品国家", "上映年份", "上映月份", "上映日期", "电影时长", "电影评分", "打分人数",
             "想看人数", "累计票房", "首日票房", "首周票房", "票房预测"],
            [movie_title, category, country, int(year), int(month), int(day), float(length), float(rating[0]),
             int(rating_number), int(wishing_number)] +
            [int(temp_box) if temp_box else 0 for temp_box in boxes]))


def main(movie_url_ids):
    filename = 'C:\\Users\\ASUS\\wzyhomework\\data_my.csv'

    # CSV文件的标题行
    fieldnames = ["电影名称", "电影类型", "出品国家", "上映年份", "上映月份", "上映日期", "电影时长", "电影评分",
                  "打分人数", "想看人数", "累计票房", "首日票房", "首周票房", "票房预测"]

    # 打开CSV文件并写入标题行
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        num = 1
        for movie_url_id in movie_url_ids:
            new_url = 'https://piaofang.maoyan.com' + movie_url_id
            print(new_url)
            text = get(new_url)  # 获取当前页面的源码
            data = get_data(text)  # 获取当前页面的电影信息
            print(num)
            print(data)
            num = num + 1
            # 写入CSV文件
            writer.writerow(data)


url = 'https://piaofang.maoyan.com/rankings/year'
resp = get(url)  # 获取目标网页的源码
print(resp)
# url_list = get_url(resp)  # 获取网页中详情页的URL列表
# print(url_list)

# 排除以下有问题网页
# url_list.remove('/movie/893')
# url_list.remove('/movie/1320283')
# 调用main函数
# main(url_list)
