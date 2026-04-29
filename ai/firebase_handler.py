import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

class FirebaseHandler:
    def __init__(self):
        if not firebase_admin._apps:
            cred = credentials.Certificate("../backend/serviceAccountKey.json")
            firebase_admin.initialize_app(cred)

        self.db = firestore.client()

    def update_pelanggan(self, cafe_id):
        today = datetime.now()
        tanggal = today.strftime("%Y-%m-%d")

        doc_ref = self.db.collection("pelanggan").document(tanggal)
        doc = doc_ref.get()

        if doc.exists:
            doc_ref.update({
                "jumlah": firestore.Increment(1)
            })
        else:
            doc_ref.set({
                "cafe_id": cafe_id,
                "jumlah": 1,
                "tanggal": tanggal,
                "bulan": today.month,
                "tahun": today.year
            })

    def save_service(self, cafe_id, table_number, waiting_time):
        today = datetime.now().strftime("%Y-%m-%d")

        self.db.collection("services").add({
            "cafe_id": cafe_id,
            "customer_code": f"C{table_number}",
            "status": "normal",
            "table_number": f"T{table_number}",
            "tanggal": today,
            "waiting_time": waiting_time
        })