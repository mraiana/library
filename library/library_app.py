from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta 
import pandas as pd
from io import BytesIO
from flask import send_file

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///library.db'
db = SQLAlchemy(app)

# Модели данных
class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    year = db.Column(db.Integer)
    quantity = db.Column(db.Integer, default=1)
    borrowings = db.relationship('Borrowing', backref='book', lazy=True)

    def __repr__(self):
        return f"<Book {self.title}>"

class Reader(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    birth_year = db.Column(db.Integer)
    grade = db.Column(db.String(10))
    borrowings = db.relationship('Borrowing', backref='reader', lazy=True)

    def __repr__(self):
        return f"<Reader {self.full_name}>"

class Borrowing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    reader_id = db.Column(db.Integer, db.ForeignKey('reader.id'), nullable=False)
    borrow_date = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.DateTime)  
    return_date = db.Column(db.DateTime)

    def __repr__(self):
        return f"<Borrowing book_id={self.book_id}, reader_id={self.reader_id}>"

with app.app_context():
    db.create_all()

# Маршруты
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/books')
def list_books():
    books = Book.query.all()
    return render_template('book_list.html', books=books)

@app.route('/books/add', methods=['GET', 'POST'])
def add_book():
    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        year = request.form['year']
        quantity = request.form['quantity']
        new_book = Book(title=title, author=author, year=year, quantity=quantity)
        db.session.add(new_book)
        db.session.commit()
        return redirect(url_for('list_books'))
    return render_template('add_book.html')

@app.route('/books/borrow/<int:book_id>', methods=['GET', 'POST'])
def borrow_book(book_id):
    book = Book.query.get_or_404(book_id)
    readers = Reader.query.all()
    if request.method == 'POST':
        reader_id = request.form['reader_id']
        due_date_str = request.form['due_date']
        due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
        reader = Reader.query.get_or_404(reader_id)
        borrowing = Borrowing(book_id=book.id, reader_id=reader.id, due_date=due_date)
        db.session.add(borrowing)
        book.quantity -= 1
        if book.quantity == 0:
            db.session.delete(book)
        db.session.commit()
        return redirect(url_for('list_borrowed_books'))
    return render_template('borrow_book.html', book=book, readers=readers)

@app.route('/readers')
def list_readers():
    readers = Reader.query.all()
    return render_template('reader_list.html', readers=readers)

@app.route('/readers/add', methods=['GET', 'POST'])
def add_reader():
    if request.method == 'POST':
        full_name = request.form['full_name']
        birth_year = request.form['birth_year']
        grade = request.form['grade']
        new_reader = Reader(full_name=full_name, birth_year=birth_year, grade=grade)
        db.session.add(new_reader)
        db.session.commit()
        return redirect(url_for('list_readers'))
    return render_template('add_reader.html')

@app.route('/borrowed')
def list_borrowed_books():
    borrowed_books = Borrowing.query.all()
    return render_template('borrowed_list.html', borrowed_books=borrowed_books)

@app.route('/books/delete/<int:book_id>')
def delete_book(book_id):
    book_to_delete = Book.query.get_or_404(book_id)
    db.session.delete(book_to_delete)
    db.session.commit()
    return redirect(url_for('list_books'))

@app.route('/analytics/borrowed_excel')
def analytics_borrowed_excel():
    borrowed_books = Borrowing.query.all()
    data = []
    for borrowing in borrowed_books:
        data.append({
            'Книга': borrowing.book.title,
            'Автор': borrowing.book.author,
            'Читатель': borrowing.reader.full_name,
            'Дата выдачи': borrowing.borrow_date.strftime('%Y-%m-%d %H:%M:%S'),
            'Срок возврата': borrowing.due_date.strftime('%Y-%m-%d') if borrowing.due_date else '',
            'Дата возврата': borrowing.return_date.strftime('%Y-%m-%d %H:%M:%S') if borrowing.return_date else ''
        })

    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Выданные книги', index=False)
    output.seek(0)

    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name='borrowed_books.xlsx')

@app.route('/borrowed/return/<int:borrowing_id>', methods=['POST'])
def mark_returned(borrowing_id):
    borrowing = Borrowing.query.get_or_404(borrowing_id)
    borrowing.returned = True
    borrowing.return_date = datetime.utcnow()
    db.session.commit()
    return redirect(url_for('list_borrowed_books'))

if __name__ == '__main__':
    with app.app_context():
        app.run(debug=True)