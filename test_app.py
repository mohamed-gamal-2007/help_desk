import unittest
from app import app, db
from models import User, Ticket, Message, Product
from flask import session

class HelpDeskTest(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['WTF_CSRF_ENABLED'] = False
        self.app = app.test_client()
        with app.app_context():
            db.create_all()
            # Add basic data
            admin = User(username='Admin', email='admin@test.com', role='admin')
            admin.set_password('123')
            emp = User(username='Employee', email='emp@test.com', role='employee')
            emp.set_password('123')
            cust = User(username='Customer', email='cust@test.com', role='customer')
            cust.set_password('123')
            db.session.add_all([admin, emp, cust])
            db.session.commit()

    def login(self, email, password):
        return self.app.post('/login', data=dict(
            email=email,
            password=password
        ), follow_redirects=True)

    def test_login_admin(self):
        response = self.login('admin@test.com', '123')
        self.assertIn(b'/admin', response.data)
        self.assertIn(b'Admin', response.data)

    def test_login_customer(self):
        response = self.login('cust@test.com', '123')
        self.assertIn(b'/chat', response.data)

    def test_submit_rating(self):
        with app.app_context():
            cust = User.query.filter_by(email='cust@test.com').first()
            ticket = Ticket(customer_id=cust.id, status='resolved')
            db.session.add(ticket)
            db.session.commit()
            tid = ticket.id

        self.login('cust@test.com', '123')
        # Use JSON for submit_rating
        response = self.app.post('/submit_rating', 
                                 json={'ticket_id': tid, 'rating': 5})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['status'], 'success')
        
        with app.app_context():
            t = Ticket.query.get(tid)
            self.assertEqual(t.rating, 5)

    def test_cascade_delete(self):
        with app.app_context():
            cust = User.query.filter_by(email='cust@test.com').first()
            ticket = Ticket(customer_id=cust.id, status='new')
            db.session.add(ticket)
            db.session.commit()
            msg = Message(ticket_id=ticket.id, sender_id=cust.id, content='Hello')
            db.session.add(msg)
            db.session.commit()
            cid = cust.id

        self.login('admin@test.com', '123')
        # Simulate CSRF check disabled in setUp
        response = self.app.get(f'/admin/users/delete/{cid}', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        
        with app.app_context():
            self.assertIsNone(User.query.get(cid))
            self.assertEqual(Ticket.query.filter_by(customer_id=cid).count(), 0)

if __name__ == '__main__':
    unittest.main()
