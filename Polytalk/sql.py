import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from sqlalchemy import desc
import random
import json

# instance klasörü yoksa oluştur
os.makedirs(os.path.join(os.path.dirname(__file__), 'instance'), exist_ok=True)

db = SQLAlchemy()

def init_app(app):
    app.config['SECRET_KEY'] = os.urandom(24)
    db_path = os.path.abspath(os.path.join('instance', 'polytalk.db'))
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)

    with app.app_context():
        db.create_all()
    print('Kullanılan veritabanı:', app.config['SQLALCHEMY_DATABASE_URI'])

class Kullanici(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    kullanici_adi = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    sifre = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_moderator = db.Column(db.Boolean, default=False)
    hedef_dil = db.Column(db.String(50))
    seviye = db.Column(db.String(20))
    olusturulma_tarihi = db.Column(db.DateTime, default=datetime.utcnow)
    son_giris = db.Column(db.DateTime)
    
    # İlişkiler
    ilerleme = db.relationship('KullaniciIlerleme', backref='kullanici', uselist=False, lazy=True)
    kelime_kartlari = db.relationship('KelimeKart', backref='kullanici', lazy=True)
    
    def __repr__(self):
        return f'<Kullanici {self.kullanici_adi}>'

class KullaniciIlerleme(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    kullanici_id = db.Column(db.Integer, db.ForeignKey('kullanici.id'), nullable=False)
    toplam_xp = db.Column(db.Integer, default=0)
    seviye = db.Column(db.Integer, default=1)
    son_guncelleme = db.Column(db.DateTime, default=datetime.utcnow)
    streak = db.Column(db.Integer, default=0)
    son_aktivite = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<KullaniciIlerleme {self.kullanici_id}>'

class KelimeKart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    kullanici_id = db.Column(db.Integer, db.ForeignKey('kullanici.id'), nullable=False)
    kelime = db.Column(db.String(100), nullable=False)
    anlam = db.Column(db.String(200), nullable=False)
    ornek = db.Column(db.Text)
    ogrenildi = db.Column(db.Boolean, default=False)
    tekrar_sayisi = db.Column(db.Integer, default=0)
    son_tekrar = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<KelimeKart {self.kelime}>'

class ChatbotAnaliz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    kullanici_id = db.Column(db.Integer, db.ForeignKey('kullanici.id'), nullable=False)
    analiz_tarihi = db.Column(db.DateTime, default=datetime.utcnow)
    sohbet_tipi = db.Column(db.String(50), default='general')  # 'general' veya 'food'
    vocabulary = db.Column(db.Text)
    grammar = db.Column(db.Text)
    pronunciation = db.Column(db.Text)
    alternatives = db.Column(db.Text)
    fluency = db.Column(db.Text)
    communication = db.Column(db.Text)
    recommendations = db.Column(db.Text)
    
    def __repr__(self):
        return f'<ChatbotAnaliz {self.id} - {self.kullanici_id}>'



def check_username_exists(kullanici_adi):
    return Kullanici.query.filter_by(kullanici_adi=kullanici_adi).first() is not None

def check_email_exists(email):
    return Kullanici.query.filter_by(email=email).first() is not None

def create_user_with_progress(kullanici_adi, email, sifre):
    try:
        yeni_kullanici = Kullanici(
            kullanici_adi=kullanici_adi,
            email=email,
            sifre=sifre
        )
        db.session.add(yeni_kullanici)
        db.session.flush()
        
        yeni_ilerleme = KullaniciIlerleme(kullanici_id=yeni_kullanici.id)
        db.session.add(yeni_ilerleme)
        
        db.session.commit()
        return yeni_kullanici, True, 'Kullanıcı başarıyla oluşturuldu!'
    except Exception as e:
        db.session.rollback()
        return None, False, f'Kullanıcı oluşturulurken bir hata oluştu: {str(e)}'

def get_user_by_credentials(kullanici_adi_veya_email, sifre):
    kullanici = Kullanici.query.filter(
        (Kullanici.kullanici_adi == kullanici_adi_veya_email) |
        (Kullanici.email == kullanici_adi_veya_email)
    ).first()
    
    if kullanici and kullanici.sifre == sifre:
        return kullanici, True
    return None, False

def get_random_word():
    kelimeler = [
        {'kelime': 'Hello', 'anlam': 'Merhaba', 'örnek': 'Hello, how are you?', 'dil': 'İngilizce'},
        {'kelime': 'Bonjour', 'anlam': 'Merhaba', 'örnek': 'Bonjour, comment allez-vous?', 'dil': 'Fransızca'},
        {'kelime': 'Hola', 'anlam': 'Merhaba', 'örnek': 'Hola, ¿cómo estás?', 'dil': 'İspanyolca'},
        {'kelime': 'Ciao', 'anlam': 'Merhaba', 'örnek': 'Ciao, come stai?', 'dil': 'İtalyanca'},
        {'kelime': 'Hallo', 'anlam': 'Merhaba', 'örnek': 'Hallo, wie geht es dir?', 'dil': 'Almanca'}
    ]
    return random.choice(kelimeler)

def get_user_cards(kullanici_id):
    return KelimeKart.query.filter_by(kullanici_id=kullanici_id).all()

def add_word_card(kullanici_id, kelime, anlam, ornek=None):
    try:
        yeni_kart = KelimeKart(
            kullanici_id=kullanici_id,
            kelime=kelime,
            anlam=anlam,
            ornek=ornek
        )
        db.session.add(yeni_kart)
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        return False

def get_admin_by_credentials(kullanici_adi_veya_email, sifre):
    admin = Kullanici.query.filter(
        ((Kullanici.kullanici_adi == kullanici_adi_veya_email) |
         (Kullanici.email == kullanici_adi_veya_email)) &
        (Kullanici.is_admin == True)
    ).first()
    if admin and admin.sifre == sifre:
        return admin
    return None

def update_user_role(kullanici_id, role):
    try:
        kullanici = Kullanici.query.get(kullanici_id)
        if kullanici:
            kullanici.is_admin = (role == 'admin')
            db.session.commit()
            return True
        return False
    except Exception as e:
        db.session.rollback()
        return False

def get_all_users():
    users = Kullanici.query.all()
    user_list = []
    for user in users:
        ilerleme = KullaniciIlerleme.query.filter_by(kullanici_id=user.id).first()
        user_list.append({
            'id': user.id,
            'kullanici_adi': user.kullanici_adi,
            'email': user.email,
            'toplam_xp': ilerleme.toplam_xp if ilerleme else 0,
            'seviye': getattr(ilerleme, 'seviye', 1) if ilerleme else 1,
            'streak': getattr(ilerleme, 'streak', 0) if ilerleme else 0,
            'is_admin': user.is_admin,
            'is_moderator': getattr(user, 'is_moderator', False),
            'olusturulma_tarihi': user.olusturulma_tarihi,
            'son_giris': user.son_giris.strftime('%Y-%m-%d %H:%M:%S') if user.son_giris else 'Hiç giriş yapmadı'
        })
    return user_list

def create_new_user(kullanici_adi, email, sifre, is_admin=False):
    try:
        yeni_kullanici = Kullanici(
            kullanici_adi=kullanici_adi,
            email=email,
            sifre=sifre,
            is_admin=is_admin
        )
        db.session.add(yeni_kullanici)
        db.session.flush()
        
        yeni_ilerleme = KullaniciIlerleme(kullanici_id=yeni_kullanici.id)
        db.session.add(yeni_ilerleme)
        
        db.session.commit()
        return True, 'Kullanıcı başarıyla oluşturuldu!'
    except Exception as e:
        db.session.rollback()
        return False, f'Kullanıcı oluşturulurken bir hata oluştu: {str(e)}'

def admin_kullanici_olustur():
    admin = Kullanici.query.filter_by(kullanici_adi='admin').first()
    if not admin:
        admin = Kullanici(
            kullanici_adi='admin',
            email='admin@polytalk.com',
            sifre='admin123',
            is_admin=True,
            olusturulma_tarihi=datetime.utcnow()
        )
        db.session.add(admin)
        db.session.commit()
        
        ilerleme = KullaniciIlerleme(kullanici_id=admin.id)
        db.session.add(ilerleme)
        db.session.commit()
    else:
        admin.sifre = 'admin123'
        admin.is_admin = True
        db.session.commit()

def get_leaderboard_data(current_user_id=None):
    kullanicilar = (
        Kullanici.query
        .join(KullaniciIlerleme, Kullanici.id == KullaniciIlerleme.kullanici_id)
        .add_columns(Kullanici.id, Kullanici.kullanici_adi, KullaniciIlerleme.toplam_xp, KullaniciIlerleme.seviye)
        .order_by(desc(KullaniciIlerleme.toplam_xp))
        .limit(20)
        .all()
    )
    
    current_user_row = None
    if current_user_id:
        all_users = (
            Kullanici.query
            .join(KullaniciIlerleme, Kullanici.id == KullaniciIlerleme.kullanici_id)
            .add_columns(Kullanici.id, Kullanici.kullanici_adi, KullaniciIlerleme.toplam_xp, KullaniciIlerleme.seviye)
            .order_by(desc(KullaniciIlerleme.toplam_xp))
            .all()
        )
        for idx, row in enumerate(all_users, 1):
            if row.id == current_user_id:
                if not any(u.id == current_user_id for u in kullanicilar):
                    current_user_row = {'rank': idx, 'kullanici_adi': row.kullanici_adi, 'toplam_xp': row.toplam_xp}
                break
    
    return kullanicilar, current_user_row

def get_user_progress_data(kullanici_id, skor=0):
    try:
        ilerleme = KullaniciIlerleme.query.filter_by(kullanici_id=kullanici_id).first()
        
        if not ilerleme:
            ilerleme = create_user_progress(kullanici_id)
        
        if skor > 0:
            ilerleme.toplam_xp += skor
            ilerleme.seviye = (ilerleme.toplam_xp // 100) + 1
            ilerleme.son_guncelleme = datetime.utcnow()
            db.session.commit()
        
        return ilerleme
    except Exception as e:
        db.session.rollback()
        return create_user_progress(kullanici_id)

def create_user_progress(kullanici_id):
    try:
        yeni_ilerleme = KullaniciIlerleme(
            kullanici_id=kullanici_id,
            toplam_xp=0,
            seviye=1,
            streak=0
        )
        db.session.add(yeni_ilerleme)
        db.session.commit()
        return yeni_ilerleme
    except Exception as e:
        db.session.rollback()
        return None



def get_daily_tasks(user_id):
    """Günlük görevleri döndürür."""
    return [
        {
            'görev_tipi': 'xp',
            'ad': 'Günlük XP Topla',
            'xp_ödülü': 10,
            'hedef': 100
        },
        {
            'görev_tipi': 'ders',
            'ad': '3 Ders Tamamla',
            'xp_ödülü': 30,
            'hedef': 3
        },
        {
            'görev_tipi': 'kelime',
            'ad': '5 Yeni Kelime Öğren',
            'xp_ödülü': 20,
            'hedef': 5
        }
    ]

def update_user_language(user_id, hedef_dil, seviye):
    """Kullanıcının hedef dil ve seviye bilgilerini günceller."""
    user = Kullanici.query.get(user_id)
    if user:
        user.hedef_dil = hedef_dil
        user.seviye = seviye
        db.session.commit()
        return True
    return False

def save_chatbot_analysis(kullanici_id, sohbet_tipi, analysis_data):
    """Chatbot analiz sonuçlarını veritabanına kaydeder"""
    try:
        analiz = ChatbotAnaliz(
            kullanici_id=kullanici_id,
            sohbet_tipi=sohbet_tipi,
            vocabulary=analysis_data.get('vocabulary', ''),
            grammar=analysis_data.get('grammar', ''),
            pronunciation=analysis_data.get('pronunciation', ''),
            alternatives=analysis_data.get('alternatives', ''),
            fluency=analysis_data.get('fluency', ''),
            communication=analysis_data.get('communication', ''),
            recommendations=analysis_data.get('recommendations', '')
        )
        db.session.add(analiz)
        db.session.commit()
        return analiz.id, True, 'Analiz başarıyla kaydedildi!'
    except Exception as e:
        db.session.rollback()
        return None, False, f'Analiz kaydedilirken hata oluştu: {str(e)}'

def get_chatbot_analysis(analiz_id):
    """Belirli bir analiz sonucunu veritabanından getirir"""
    try:
        analiz = ChatbotAnaliz.query.get(analiz_id)
        if analiz:
            return {
                'vocabulary': analiz.vocabulary,
                'grammar': analiz.grammar,
                'pronunciation': analiz.pronunciation,
                'alternatives': analiz.alternatives,
                'fluency': analiz.fluency,
                'communication': analiz.communication,
                'recommendations': analiz.recommendations
            }, True, 'Analiz bulundu!'
        return None, False, 'Analiz bulunamadı!'
    except Exception as e:
        return None, False, f'Analiz getirilirken hata oluştu: {str(e)}'

def get_user_latest_analysis(kullanici_id, sohbet_tipi='general'):
    """Kullanıcının en son analiz sonucunu getirir"""
    try:
        analiz = ChatbotAnaliz.query.filter_by(
            kullanici_id=kullanici_id, 
            sohbet_tipi=sohbet_tipi
        ).order_by(ChatbotAnaliz.analiz_tarihi.desc()).first()
        
        if analiz:
            return {
                'id': analiz.id,
                'vocabulary': analiz.vocabulary,
                'grammar': analiz.grammar,
                'pronunciation': analiz.pronunciation,
                'alternatives': analiz.alternatives,
                'fluency': analiz.fluency,
                'communication': analiz.communication,
                'recommendations': analiz.recommendations,
                'analiz_tarihi': analiz.analiz_tarihi
            }, True, 'Analiz bulundu!'
        return None, False, 'Analiz bulunamadı!'
    except Exception as e:
        return None, False, f'Analiz getirilirken hata oluştu: {str(e)}'

 