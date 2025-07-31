from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from flask_login import login_user, logout_user, login_required, current_user
from sql import (
    db, Kullanici, KullaniciIlerleme, KelimeKart,
    check_username_exists, check_email_exists, create_user_with_progress,
    get_user_by_credentials, get_user_cards, add_word_card,
    get_user_progress_data, create_user_progress
)
from utils import get_user_reports, create_pdf, create_csv, create_cards_pdf
import re
from datetime import datetime

kullanici_bp = Blueprint('kullanici', __name__)

def admin_required(f):
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Bu sayfaya erişim yetkiniz yok!', 'error')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

def validate_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

@kullanici_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        kullanici_adi = request.form.get('kullanici_adi')
        email = request.form.get('email')
        sifre = request.form.get('sifre')
        
        if not kullanici_adi or not email or not sifre:
            flash('Tüm alanları doldurun!', 'error')
            return redirect(url_for('kullanici.register'))
        
        if not validate_email(email):
            flash('Geçerli bir email adresi girin!', 'error')
            return redirect(url_for('kullanici.register'))
        
        if check_username_exists(kullanici_adi):
            flash('Bu kullanıcı adı zaten kullanılıyor!', 'error')
            return redirect(url_for('kullanici.register'))
        
        if check_email_exists(email):
            flash('Bu email adresi zaten kullanılıyor!', 'error')
            return redirect(url_for('kullanici.register'))
        
        user, success, message = create_user_with_progress(kullanici_adi, email, sifre)
        
        if success:
            flash(message, 'success')
            login_user(user)
            return redirect(url_for('dil_secimi'))
        else:
            flash(message, 'error')
            return redirect(url_for('kullanici.register'))
    
    return render_template('register.html')

@kullanici_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        kullanici_adi_veya_email = request.form.get('kullanici_adi_veya_email')
        sifre = request.form.get('sifre')
        
        if not kullanici_adi_veya_email or not sifre:
            flash('Tüm alanları doldurun!', 'error')
            return redirect(url_for('kullanici.login'))
        
        user, success = get_user_by_credentials(kullanici_adi_veya_email, sifre)
        
        if success:
            # Son giriş zamanını güncelle
            user.son_giris = datetime.utcnow()
            db.session.commit()
            
            login_user(user)
            flash('Başarıyla giriş yaptınız!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Geçersiz kullanıcı adı/e-posta veya şifre!', 'error')
            return redirect(url_for('kullanici.login'))
    
    return render_template('login.html')

@kullanici_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Başarıyla çıkış yaptınız!', 'success')
    return redirect(url_for('index'))

@kullanici_bp.route('/profile')
@login_required
def profile():
    try:
        # Kullanıcı ilerleme verilerini al
        user_progress = get_user_progress_data(current_user.id)
        if not user_progress:
            user_progress = create_user_progress(current_user.id)
            if not user_progress:
                flash('Kullanıcı ilerleme verileri oluşturulamadı.', 'error')
                return redirect(url_for('index'))
        
        # Rapor verilerini al
        plot_url, stats = get_user_reports(current_user.id)
        
        return render_template('profile.html', 
                             plot_url=plot_url, 
                             stats=stats, 
                             user_progress=user_progress)
    except Exception as e:
        flash(f'Bir hata oluştu: {str(e)}', 'error')
        return redirect(url_for('index'))

@kullanici_bp.route('/my_cards')
@login_required
def my_cards():
    kartlar = get_user_cards(current_user.id)
    return render_template('my_cards.html', kartlar=kartlar)

@kullanici_bp.route('/add_card', methods=['GET', 'POST'])
@login_required
def add_card():
    if request.method == 'POST':
        kelime = request.form.get('kelime')
        anlam = request.form.get('anlam')
        örnek = request.form.get('örnek')
        
        if not kelime or not anlam:
            flash('Kelime ve anlam alanları zorunludur!', 'error')
            return redirect(url_for('kullanici.my_cards'))
        
        if add_word_card(current_user.id, kelime, anlam, örnek):
            flash('Kelime kartı başarıyla eklendi!', 'success')
        else:
            flash('Kelime kartı eklenirken bir hata oluştu.', 'error')
        
        return redirect(url_for('kullanici.my_cards'))
    
    return redirect(url_for('kullanici.my_cards'))

@kullanici_bp.route('/download_pdf')
@login_required
def download_pdf():
    try:
        pdf_path = create_pdf(current_user.id)
        return send_file(pdf_path, as_attachment=True, download_name=f'rapor_{current_user.kullanici_adi}.pdf')
    except Exception as e:
        flash(f'PDF oluşturulurken hata oluştu: {str(e)}', 'error')
        return redirect(url_for('kullanici.reports'))

@kullanici_bp.route('/download_csv')
@login_required
def download_csv():
    try:
        csv_path = create_csv(current_user.id)
        return send_file(csv_path, as_attachment=True, download_name=f'rapor_{current_user.kullanici_adi}.csv')
    except Exception as e:
        flash(f'CSV oluşturulurken hata oluştu: {str(e)}', 'error')
        return redirect(url_for('kullanici.reports'))

@kullanici_bp.route('/update_progress', methods=['POST'])
@login_required
def update_progress():
    skor = int(request.form.get('skor', 0))
    get_user_progress_data(current_user.id, skor)
    flash('İlerlemeniz güncellendi!', 'success')
    return redirect(url_for('kullanici.profile'))

@kullanici_bp.route('/download_cards_pdf')
@login_required
def download_cards_pdf():
    try:
        kartlar = get_user_cards(current_user.id)
        if not kartlar:
            flash('Henüz kelime kartınız bulunmuyor.', 'warning')
            return redirect(url_for('kullanici.my_cards'))
        
        # PDF oluştur
        pdf_buffer = create_cards_pdf(kartlar)
        return send_file(
            pdf_buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name='kelime_kartlari.pdf'
        )
    except Exception as e:
        flash(f'PDF oluşturulurken bir hata oluştu: {str(e)}', 'error')
        return redirect(url_for('kullanici.my_cards'))

@kullanici_bp.route('/download_cards_csv')
@login_required
def download_cards_csv():
    try:
        kartlar = get_user_cards(current_user.id)
        if not kartlar:
            flash('Henüz kelime kartınız bulunmuyor.', 'warning')
            return redirect(url_for('kullanici.my_cards'))
        
        # CSV oluştur
        csv_buffer = create_csv(kartlar)
        return send_file(
            csv_buffer,
            mimetype='text/csv',
            as_attachment=True,
            download_name='kelime_kartlari.csv'
        )
    except Exception as e:
        flash(f'CSV oluşturulurken bir hata oluştu: {str(e)}', 'error')
        return redirect(url_for('kullanici.my_cards'))

@kullanici_bp.route('/reports')
@login_required
def reports():
    """
    Kullanıcı ilerleme ve raporlarını gösteren sayfa.
    """
    try:
        # Kullanıcı ilerleme verilerini al
        user_progress = get_user_progress_data(current_user.id)
        if not user_progress:
            user_progress = create_user_progress(current_user.id)
            if not user_progress:
                flash('Kullanıcı ilerleme verileri oluşturulamadı.', 'error')
                return redirect(url_for('index'))
        
        # Rapor verilerini al
        plot_url, stats = get_user_reports(current_user.id)
        
        return render_template('reports.html', 
                             plot_url=plot_url, 
                             stats=stats, 
                             user_progress=user_progress)
    except Exception as e:
        flash(f'Bir hata oluştu: {str(e)}', 'error')
        return redirect(url_for('index')) 