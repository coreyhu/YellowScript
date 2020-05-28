from flask import Flask, request, render_template, Response
from scraper import parse_categories

app = Flask(__name__, template_folder="templates")

@app.route('/')
def my_form():
    return render_template("form.html")

dataframes = {}

@app.route('/', methods=['POST'])
def my_form_post():

    city = request.form['city']
    state = request.form['state']
    kw = request.form['keywords']
    seperate = False  # TODO : download each keyword as seperate csvs
    kw = [word.strip() for word in kw.split(",") if word.strip()]

    df = parse_categories(category_keywords=kw, city=city, state=state, seperate=seperate)
    csv = df.to_csv()

    return Response(
        csv,
        mimetype="text/csv",
        headers={"Content-disposition":
                 "attachment; filename=scraped.csv"})


if __name__ == '__main__':
    app.run(development=True)
