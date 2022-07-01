import os
import sys
import csv
import datetime
from dateutil.relativedelta import relativedelta
import time
import requests
from bs4 import BeautifulSoup
import gspread
from oauth2client.service_account import ServiceAccountCredentials      #ServiceAccountCredentials：Googleの各サービスへアクセスできるservice変数を生成する


#スプレッドシートに書き込む     引数 row:行, column:列, export_data:出力するデータ
def write_spread_sheet(row, column, export_data) :
    if export_data != '' :
        worksheet.update_cell(row, column, export_data)
        time.sleep(1)


#情報を入力
scraping_url = input('スクレイピングするレースの出馬表(netkeiba)のURLを入力してください：')
write_csv_file = input('結果を出力するCSVファイルを入力してください(入力しない場合ファイルが新規作成されます)：')

if write_csv_file == '' :
    write_csv_file = os.path.dirname(sys.argv[0]) + '/organized_data.csv'

elif not os.path.exists(write_csv_file) :
    print('入力した場所にファイルがありません')
    exit()

json_keyfile_name = input('スプレッドシートを読み書きする際に必要なjsonファイルを入力してください：')

if not os.path.exists(json_keyfile_name) :
    print('入力した場所にファイルがありません')
    exit()

spreadsheet_key = input('結果を出力するスプレッドシートのスプレッドシートキーを入力してください：')


headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
}
session = requests.session()

#設定したURLをクローリング
print('\n' + scraping_url + 'をスクレイピング')

req = session.get(scraping_url, headers = headers)
soup = BeautifulSoup(req.content, 'html.parser')

#レース情報をスクレイピング
race_place = soup.select('.RaceData02 > span')[1].get_text()
race_number = soup.select_one('.RaceNum').get_text()
race_type = soup.select_one('.RaceData01 > span').get_text()[1]
race_distance = int(soup.select_one('.RaceData01 > span').get_text()[2:6])
race_heads = soup.select('.RaceData02 > span')[7].get_text()

race_date_pos = soup.select_one('#RaceList_DateList > .Active > a')['href'].find('kaisai_date') + 12
race_date_str = soup.select_one('#RaceList_DateList > .Active > a')['href'][race_date_pos : race_date_pos + 8]
race_date = datetime.datetime.strptime(race_date_str, '%Y%m%d').date()

limited_date = race_date - relativedelta(years=2)  #2年前の日付

if race_distance <= 1800 :      #1800m以下なら
    race_distance_range = 200
else :                          #1900m以上なら
    race_distance_range = 400

if race_distance % 200 != 0 :   #奇数距離なら(ex.1700,2100)
    race_distance_range += 100

print(race_date.strftime('%Y/%m/%d'), race_place + race_number, race_type + str(race_distance) + 'm', race_heads)

num = 0
stock_data = list()             #データを蓄積するための空のリスト
links = soup.select('.HorseName > a')   #競走馬名とその馬の競走成績URLを取得
for link in links :
    title = link.attrs['title']
    href = link.attrs['href']
    num += 1

    print(num, title, href)
    stock_data.append([title])

    time.sleep(2)     #2s待機(短時間での大量アクセスを防ぐため)

    url = href
    req = session.get(url, headers = headers)
    soup = BeautifulSoup(req.content, 'html.parser')

    table = soup.select_one('.db_h_race_results, .contents')

    if table.get_text() == '競走データがありません' :    #初出走ならば
        stock_data.append([])

    else :
        trs = table.select('tr')

        for tr in trs :
            data = list()

            for cell in tr.select('th, td') :
                data.append(cell.get_text())
                
            stock_data.append(data)

num = 0
organized_race_data = list()    #整理したデータを保存するための空のリスト

for row in stock_data:
    if row[0] != '' and row[0] != '日付' :
        if not '/' in row[0] :  #競走馬名ならば
            num += 1
            course_record = [0, 0, 0, 0]    #同コースにおける成績
            place_record = [0, 0, 0, 0]     #同場所における成績
            distance_record = [0, 0, 0, 0]  #同距離における成績

            horse_name = row[0]

            organized_race_data.append([num, horse_name, course_record, place_record, distance_record])  #末尾に一頭分のデータを追加
        
        else :      #日付ならば
            date = datetime.datetime.strptime(row[0], '%Y/%m/%d').date()

            if limited_date <= date < race_date :
                if row[11] != '除' and row[11] != '取' and row[11] != '中' and row[11] != '' :    #順位の除外と取り消しと中止と空欄を除く
                    place = row[1]
                    rank = int(row[11])
                    type = row[14][0]
                    distance = int(row[14][1:])

                    if type == race_type :     #指定の種類(ex.芝)のデータのみ抽出
                        if race_place in place :   #指定の場所(ex.東京)のデータのみ抽出                            
                            if distance == race_distance :     #指定の距離(ex.1600)のデータのみ抽出 course_recordのデータを上書き
                                if rank <= 3 :                     #3位以内なら
                                    organized_race_data[num - 1][2][rank - 1] += 1
                                else :                                  #4位以下なら
                                    organized_race_data[num - 1][2][3] += 1

                            if (race_distance - race_distance_range) <= distance <= (race_distance + race_distance_range) : #指定の距離の間(ex.1400-1800)のデータのみ抽出 place_recordのデータを上書き
                                if rank <= 3 :                     #3位以内なら
                                    organized_race_data[num - 1][3][rank - 1] += 1
                                else :                                  #4位以下なら
                                    organized_race_data[num - 1][3][3] += 1

                        if distance == race_distance :     #全ての場所の指定の距離(ex.1600)のデータのみ抽出 distance_recordのデータを上書き
                            if rank <= 3 :                         #3位以内なら
                                organized_race_data[num - 1][4][rank - 1] += 1
                            else :                                      #4位以下なら
                                organized_race_data[num - 1][4][3] += 1

#CSVファイルにデータを書き込む
print('\n' + write_csv_file + 'に書き込み')

for row in organized_race_data :
    print(row)

with open(write_csv_file, 'w') as f :
    writer = csv.writer(f)

    writer.writerow([race_date.strftime('%Y/%m/%d') + ' ' + race_place + race_number + ' ' + race_type + str(race_distance) + 'm'])
    writer.writerow(['馬番', '馬名', race_place + str(race_distance) + 'm','','','', race_place + str(race_distance - race_distance_range) + '-' + str(race_distance + race_distance_range) + 'm','','','', '全場所' + str(race_distance) + 'm','','',''])

    for row in organized_race_data :
        extended_list = [row[0], row[1]]
        extended_list.extend(row[2])
        extended_list.extend(row[3])
        extended_list.extend(row[4])

        writer.writerow(extended_list)
f.close()

#スプレッドシートにデータを書き込む
print('\nスプレッドシートに書き込み')

scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']   #2つのAPIを記述しないとリフレッシュトークンを3600秒毎に発行し続けなければならない

credentials = ServiceAccountCredentials.from_json_keyfile_name(json_keyfile_name, scope)    #jsonファイル名をクレデンシャル変数に設定

gc = gspread.authorize(credentials) #OAuth2の資格情報を使用してGoogle APIにログイン

worksheet = gc.open_by_key(spreadsheet_key).worksheet(race_number)  #スプレッドシートを開く

race_data = race_date.strftime('%Y/%m/%d') + ' ' + race_place + race_number + ' ' + race_type + str(race_distance) + 'm'
write_spread_sheet(1, 1, race_data)
print(race_data)

title_list = ['馬番', '馬名', race_place + str(race_distance) + 'm','','','', race_place + str(race_distance - race_distance_range) + '-' + str(race_distance + race_distance_range) + 'm','','','', '全場所' + str(race_distance) + 'm','','','']
column_num = 1
for cell in title_list :
    write_spread_sheet(2, column_num, cell)
    column_num += 1

for row in organized_race_data :
    extended_list = [row[0], row[1]]

    if sum(row[2]) == 0 :
        extended_list.extend(['','','',''])
    else :
        extended_list.extend(row[2])
    if sum(row[3]) == 0 :
        extended_list.extend(['','','',''])
    else :
        extended_list.extend(row[3])
    if sum(row[4]) == 0 :
        extended_list.extend(['','','',''])
    else :
        extended_list.extend(row[4])

    print(row[0], row[1])

    column_num = 1
    row_num = extended_list[0] + 2
    for cell in extended_list :
        write_spread_sheet(row_num, column_num, cell)
        column_num += 1

print('\nプログラム完了')
