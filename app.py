from flask import Flask
from flask import render_template
from flask import request
from Scraper import *
from flask import send_from_directory
from flask_sqlalchemy import SQLAlchemy
import itertools
from Transform import *


app = Flask(__name__)
app.config['SECRET_KEY'] = 'thatisasecret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:Banana6543210@localhost/ETLdb'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class ScrapTable(db.Model):
    __tablename__ = 'ScrapTable'
    id = db.Column(db.Integer, primary_key=True)
    location = db.Column(db.String(200))
    rooms = db.Column(db.String(200))
    price = db.Column(db.String(200))
    area = db.Column(db.String(200))

    def __init__(self, location, rooms, price, area):
        self.location = location
        self.rooms = rooms
        self.price = price
        self.area = area

class TransformTable(db.Model):
    __tablename__ = 'TransformTable'
    id = db.Column(db.Integer, primary_key=True)
    location = db.Column(db.String(100))
    rooms = db.Column(db.Integer)
    price = db.Column(db.Integer)
    area = db.Column(db.Numeric(precision=2))

    def __init__(self, location, rooms, price, area):
        self.location = location
        self.rooms = rooms
        self.price = price
        self.area = area

@app.route('/', methods=['GET', 'POST'])
def render_home():
    if request.method == 'GET':
        db.session.query(ScrapTable).delete()
        db.session.commit()
        return render_template('main.html')

@app.route('/extract', methods=['GET', 'POST'])
def extract():
    req = request.form
    pages = int(req.get("pages"))
    scraper = WebScraper(pages)
    scraper.run()
    scResults =scraper.results
    loc = [sub['location'] for sub in scResults]
    pri = [sub['price'] for sub in scResults]
    are = [sub['area'] for sub in scResults]
    roo = [sub['rooms'] for sub in scResults]

    for (a, b, c, d) in itertools.zip_longest(loc, roo, pri, are):
        record = db.session.query(ScrapTable).filter(ScrapTable.location==a, ScrapTable.rooms==b, ScrapTable.price==c, ScrapTable.area==d).one_or_none()
        if record:
            print('Rekord juz istnieje')
        else:
            data = ScrapTable(a, b, c, d)
            db.session.add(data)
            db.session.commit()

    locations_db = db.session.query(ScrapTable.location).all()
    rooms_db = db.session.query(ScrapTable.rooms).all()
    prices_db = db.session.query(ScrapTable.price).all()
    area_db = db.session.query(ScrapTable.area).all()

    final_results_db = []
    for index in range(0, len(locations_db)):
        final_results_db.append({
            'location': locations_db[index],
            'rooms': rooms_db[index],
            'price': prices_db[index],
            'area': area_db[index]
        })
    leng2 = len(locations_db)
    return render_template('home.html', extracted=final_results_db, leng = leng2)

@app.route('/download')
def download():
    return send_from_directory('', 'all_offers.csv', as_attachment=True)

@app.route('/clear')
def clear():
    db.session.query(TransformTable).delete()
    db.session.query(ScrapTable).delete()
    db.session.commit()
    return render_template('main.html')


@app.route('/download_final')
def download_final():
    return send_from_directory('', 'all_loaded.csv', as_attachment=True)

@app.route('/etl', methods=['GET', 'POST'])
def etl():
    req = request.form
    pages = int(req.get("pages"))
    scraper = WebScraper(pages)
    scraper.run()
    scResults = scraper.results
    loc = [sub['location'] for sub in scResults]
    pri = [sub['price'] for sub in scResults]
    are = [sub['area'] for sub in scResults]
    roo = [sub['rooms'] for sub in scResults]
    for (a, b, c, d) in itertools.zip_longest(loc, roo, pri, are):
        data = ScrapTable(a, b, c, d)
        db.session.add(data)
        db.session.commit()

    locations = db.session.query(ScrapTable.location).all()
    rooms = db.session.query(ScrapTable.rooms).all()
    prices = db.session.query(ScrapTable.price).all()
    area = db.session.query(ScrapTable.area).all()

    transformer = TransformClass(locations, rooms, prices, area)
    transformer.run()

    result_loc = transformer.result_loc
    result_room = transformer.result_room
    result_pric = transformer.result_pric
    result_area = transformer.result_area

    #Database commit part
    counter = 0
    for (x, y, z, b) in itertools.zip_longest(result_loc, result_room, result_pric, result_area):
        record = db.session.query(TransformTable).filter(TransformTable.location==x, TransformTable.rooms==y, TransformTable.price==z, TransformTable.area==b).one_or_none()
        if record:
            print('Rekord juz istnieje')
        else:
            counter += 1
            data = TransformTable(x, y, z, b)
            db.session.add(data)
            db.session.commit()


    locations_tra = db.session.query(TransformTable.location).all()
    rooms_tra = db.session.query(TransformTable.rooms).all()
    prices_tra = db.session.query(TransformTable.price).all()
    area_tra = db.session.query(TransformTable.area).all()

    final_results = []
    for index in range(0, len(locations_tra)):
        final_results.append({
            'location': locations_tra[index],
            'rooms': rooms_tra[index],
            'price': prices_tra[index],
            'area': area_tra[index]
        })
    all_len = len(locations_tra)
    with open('all_loaded.csv', 'w', encoding='utf-8') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=final_results[0].keys())
        writer.writeheader()

        for row in final_results:
            writer.writerow(row)


    return render_template('load.html', results=final_results, counter=counter, all_len=all_len)

@app.route('/transform', methods=['GET', 'POST'])
def transform():
    # for row in db.session.query(ScrapTable.location).all():
    #     print(row)
    locations = db.session.query(ScrapTable.location).all()
    rooms = db.session.query(ScrapTable.rooms).all()
    prices = db.session.query(ScrapTable.price).all()
    area = db.session.query(ScrapTable.area).all()

    transformer = TransformClass(locations, rooms, prices, area)
    transformer.run()

    result_loc = transformer.result_loc
    result_room = transformer.result_room
    result_pric = transformer.result_pric
    result_area = transformer.result_area

    #Database commit part
    counter = 0
    for (x, y, z, b) in itertools.zip_longest(result_loc, result_room, result_pric, result_area):
        record = db.session.query(TransformTable).filter(TransformTable.location == x, TransformTable.rooms == y,
                                                         TransformTable.price == z,
                                                         TransformTable.area == b).one_or_none()
        if record:
            print('Rekord juz istnieje')
        else:
            counter += 1
            data = TransformTable(x, y, z, b)
            db.session.add(data)
            db.session.commit()

    return render_template('transform.html', counter=counter)



@app.route('/load', methods=['GET', 'POST'])
def load():

    locations_tra = db.session.query(TransformTable.location).all()
    rooms_tra = db.session.query(TransformTable.rooms).all()
    prices_tra = db.session.query(TransformTable.price).all()
    area_tra = db.session.query(TransformTable.area).all()

    final_results = []
    for index in range(0, len(locations_tra)):
        final_results.append({
            'location': locations_tra[index],
            'rooms': rooms_tra[index],
            'price': prices_tra[index],
            'area': area_tra[index]
        })
    all_len = len(locations_tra)
    with open('all_loaded.csv', 'w', encoding='utf-8') as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=final_results[0].keys())
        writer.writeheader()

        for row in final_results:
            writer.writerow(row)


    return render_template('load.html', results=final_results, all_len=all_len)



if __name__ == '__main__':
    app.run(debug=True, threaded=True)