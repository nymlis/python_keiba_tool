import csv
import datetime
import time
import requests
from bs4 import BeautifulSoup

#定数定義
WRITE_CSV_FILE = './write_organized_data.csv'       #整理したデータを保存するCSVファイル
SCRAPING_URL = 'https://race.netkeiba.com/race/shutuba.html?race_id=202209030411&rf=race_list'   #スクレイピングするURL

RACE_DISTANCE_RANGE = 400
LIMITED_DATE = datetime.date(2021,1,1)  #2021/1/1以降のデータを抽出

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
}
session = requests.session()

#設定したURLをクローリング
req = session.get(SCRAPING_URL, headers = headers)
soup = BeautifulSoup(req.content, 'html.parser')

#レース情報をスクレイピング
race_date = soup.select_one('#RaceList_DateList > .Active').get_text()[:-4].replace('月', '/')
race_place = soup.select('.RaceData02 > span')[1].get_text()
race_number = soup.select_one('.RaceNum').get_text()
race_type = soup.select_one('.RaceData01 > span').get_text()[1]
race_distance = int(soup.select_one('.RaceData01 > span').get_text()[2:6])
race_heads = soup.select('.RaceData02 > span')[7].get_text()

print(race_date, race_place + race_number, race_type + str(race_distance) + 'm', race_heads)

num = 0
stock_data = list()             #データを蓄積するための空のリスト
links = soup.select('.HorseName > a')   #競走馬名とその馬の競走成績URLを取得
for link in links :
    title = link.attrs['title']
    href = link.attrs['href']
    num += 1

    print(num, title, href)
    stock_data.append([title])

    time.sleep(2)     #2s待機

    url = href
    req = session.get(url, headers = headers)
    soup = BeautifulSoup(req.content, 'html.parser')

    table = soup.select_one('.db_h_race_results')
    trs = table.select('tr')

    for tr in trs :
        data = list()

        for cell in tr.select('th, td') :
            data.append(cell.get_text())
            
        stock_data.append(data)

num = 0
course_record = [0, 0, 0, 0]    #同コースにおける成績
place_record = [0, 0, 0, 0]     #同場所における成績
distance_record = [0, 0, 0, 0]  #同距離における成績
organized_race_data = list()    #整理したデータを保存するための空のリスト

for row in stock_data:
    if row[0] != '' and row[0] != '日付' :
        if not '/' in row[0] :  #競走馬名ならば
            num += 1                            #N番目のデータ
            course_record = [0, 0, 0, 0]        #リセット
            place_record = [0, 0, 0, 0] 
            distance_record = [0, 0, 0, 0]

            horse_name = row[0]

            organized_race_data.append([num, horse_name, course_record, place_record, distance_record])  #末尾に一頭分のデータを追加
        
        else :      #日付ならば
            data = datetime.datetime.strptime(row[0], '%Y/%m/%d').date()

            if data >= LIMITED_DATE :
                if row[11] != '除' and row[11] != '取' and row[11] != '中' :    #順位の除外と取り消しと中止を除く
                    place = row[1]
                    rank = int(row[11])
                    type = row[14][0]
                    distance = int(row[14][1:])
                    condition = row[15]
                    time = row[17]

                    if type == race_type :     #指定の種類(ex.芝)のデータのみ抽出
                        if race_place in place :   #指定の場所(ex.東京)のデータのみ抽出                            
                            if distance == race_distance :     #指定の距離(ex.1600)のデータのみ抽出 course_recordのデータを上書き
                                if rank <= 3 :                     #3位以内なら
                                    organized_race_data[num - 1][2][rank - 1] += 1
                                else :                                  #4位以下なら
                                    organized_race_data[num - 1][2][3] += 1

                            if (race_distance - RACE_DISTANCE_RANGE) <= distance <= (race_distance + RACE_DISTANCE_RANGE) : #指定の距離の間(ex.1400-1800)のデータのみ抽出 place_recordのデータを上書き
                                if rank <= 3 :                     #3位以内なら
                                    organized_race_data[num - 1][3][rank - 1] += 1
                                else :                                  #4位以下なら
                                    organized_race_data[num - 1][3][3] += 1

                        if distance == race_distance :     #全ての場所の指定の距離(ex.1600)のデータのみ抽出 distance_recordのデータを上書き
                            if rank <= 3 :                         #3位以内なら
                                organized_race_data[num - 1][4][rank - 1] += 1
                            else :                                      #4位以下なら
                                organized_race_data[num - 1][4][3] += 1

for row in organized_race_data :
    print(row)

with open(WRITE_CSV_FILE, 'w') as f :
    writer = csv.writer(f)

    writer.writerow([race_date + ' ' + race_place + race_number + ' ' + race_type + str(race_distance) + 'm'])
    writer.writerow(['馬番', '馬名', race_place + str(race_distance) + 'm','','','', race_place + str(race_distance - RACE_DISTANCE_RANGE) + '-' + str(race_distance + RACE_DISTANCE_RANGE) + 'm','','','', '全場所' + str(race_distance) + 'm','','',''])

    for row in organized_race_data :
        extended_list = [row[0], row[1]]
        extended_list.extend(row[2])
        extended_list.extend(row[3])
        extended_list.extend(row[4])

        writer.writerow(extended_list)
