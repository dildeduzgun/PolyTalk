# Polytalk Ana Uygulama Dosyası
# Sorumlu: Sıla Kısa  -  Tüm ana yapılandırmasını, rota tanımlarını ve temel başlatma işlemlerini yönetir
# Bu dosya, Flask uygulamasının ana yapılandırmasını ve tüm route/fonksiyonları içerir.

from flask import Flask, render_template, request, redirect, url_for, flash, send_file, abort, session
from flask_login import LoginManager, login_required, current_user, login_user
from sql import (
    db, Kullanici, KullaniciIlerleme, KelimeKart, ChatbotAnaliz,
    init_app, get_random_word, get_user_cards, add_word_card,
    get_admin_by_credentials, update_user_role, get_all_users,
    create_new_user, admin_kullanici_olustur, get_leaderboard_data,
    get_user_progress_data,
    get_daily_tasks, update_user_language, create_user_progress,
    save_chatbot_analysis, get_chatbot_analysis, get_user_latest_analysis
)
from utils import get_user_reports, create_pdf, create_csv, generate_gemini_mc_questions, generate_chatbot_response, analyze_chatbot_conversation
import os
import json
import random
from datetime import datetime
from kullanici import kullanici_bp
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///polytalk.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Veritabanını başlat
init_app(app)

# Flask-Login yapılandırması
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'kullanici.login'

@login_manager.user_loader
def load_user(user_id):
    """
    Kullanıcıyı ID ile veritabanından yükler (Flask-Login için).
    """
    return Kullanici.query.get(int(user_id))

# Kullanıcı işlemleri için blueprint'i kaydet
app.register_blueprint(kullanici_bp)

@app.route('/')
def index():
    """
    Ana sayfa. Günlük kelimeyi gösterir.
    """
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('home'))
    günlük_kelime = {
        'kelime': 'Hello',
        'anlam': 'Merhaba',
        'örnek': 'Hello, how are you?',
        'dil': 'İngilizce'
    }
    return render_template('index.html', günlük_kelime=günlük_kelime)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """
    Admin kullanıcıların giriş yapmasını sağlar.
    Kullanıcı adı ve şifreyi kontrol eder, başarılıysa admin paneline yönlendirir.
    """
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('home'))
    if request.method == 'POST':
        kullanici_adi = request.form.get('kullanici_adi_veya_email')
        sifre = request.form.get('sifre')
        
        admin = get_admin_by_credentials(kullanici_adi, sifre)
        if admin:
            # Son giriş zamanını güncelle
            admin.son_giris = datetime.utcnow()
            db.session.commit()
            
            login_user(admin)
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Geçersiz kullanıcı adı veya şifre!', 'error')
            return redirect(url_for('admin_login'))
    
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    """
    Admin paneli ana sayfası. Tüm kullanıcıları listeler.
    Sadece admin yetkisi olanlar erişebilir.
    """
    if not current_user.is_admin:
        flash('Bu sayfaya erişim yetkiniz yok!', 'error')
        return redirect(url_for('home'))
    
    kullanicilar = get_all_users()
    return render_template('admin_dashboard.html', kullanicilar=kullanicilar)

@app.route('/admin/users')
@login_required
def admin_users():
    """
    Admin panelinde kullanıcı listesini ve loglarını gösterir.
    Sadece admin yetkisi olanlar erişebilir.
    """
    if not current_user.is_admin:
        flash('Bu sayfaya erişim yetkiniz yok!', 'error')
        return redirect(url_for('home'))
    
    users = get_all_users()
    user_logs = {user['id']: [] for user in users}  # Şimdilik boş log listesi gönderiyoruz
    return render_template('admin_users.html', users=users, user_logs=user_logs)

@app.route('/admin/add_user', methods=['GET', 'POST'])
@login_required
def admin_add_user():
    """
    Admin panelinden yeni kullanıcı eklemeyi sağlar.
    Sadece admin yetkisi olanlar erişebilir.
    """
    if not current_user.is_admin:
        flash('Bu sayfaya erişim yetkiniz yok!', 'error')
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        kullanici_adi = request.form.get('kullanici_adi')
        email = request.form.get('email')
        sifre = request.form.get('sifre')
        is_admin = bool(request.form.get('is_admin'))
        
        success, message = create_new_user(kullanici_adi, email, sifre, is_admin)
        flash(message, 'success' if success else 'error')
        
        if success:
            return redirect(url_for('admin_users'))
    
    return render_template('admin_add_user.html')

@app.route('/admin/change_role', methods=['POST'])
@login_required
def admin_change_role():
    """
    Admin panelinde kullanıcı yetkisini (admin/moderatör/kullanıcı) değiştirir.
    Sadece admin yetkisi olanlar erişebilir.
    """
    if not current_user.is_admin:
        flash('Bu sayfaya erişim yetkiniz yok!', 'error')
        return redirect(url_for('index'))
    
    kullanici_id = request.form.get('kullanici_id')
    role = request.form.get('role')
    
    if update_user_role(kullanici_id, role):
        flash('Kullanıcı yetkisi güncellendi.', 'success')
    else:
        flash('Kullanıcı bulunamadı.', 'error')
    
    return redirect(url_for('admin_users'))

@app.route('/leaderboard')
def leaderboard():
    """
    Kullanıcılar arası sıralama tablosunu (leaderboard) gösterir.
    """
    kullanicilar, current_user_row = get_leaderboard_data(current_user.id if current_user.is_authenticated else None)
    return render_template('leaderboard.html', kullanicilar=kullanicilar, current_user_row=current_user_row)

@app.route('/profile')
@login_required
def profile():
    """
    Kullanıcı profil sayfası. İlerleme, istatistik ve raporları gösterir.
    """
    # Önce kullanıcı ilerleme verilerini al
    user_progress = get_user_progress_data(current_user.id)
    if not user_progress:
        user_progress = create_user_progress(current_user.id)
        if not user_progress:
            flash('Kullanıcı ilerleme verileri oluşturulamadı.', 'error')
            return redirect(url_for('home'))
    
    # Sonra rapor verilerini al
            plot_url, stats = get_user_reports(current_user.id)
    
    return render_template('profile.html', 
                         plot_url=plot_url, 
                         stats=stats, 

                         user_progress=user_progress)

@app.route('/download_pdf')
@login_required
def download_pdf():
    """
    Kullanıcıya ait ilerleme raporunu PDF olarak indirir.
    """
    try:
        pdf_path = create_pdf(current_user.id)
        return send_file(pdf_path, as_attachment=True, download_name=f'rapor_{current_user.kullanici_adi}.pdf')
    except Exception as e:
        flash(f'PDF oluşturulurken hata oluştu: {str(e)}', 'error')
        return redirect(url_for('reports'))

@app.route('/download_csv')
@login_required
def download_csv():
    """
    Kullanıcıya ait ilerleme raporunu CSV olarak indirir.
    """
    try:
        csv_path = create_csv(current_user.id)
        return send_file(csv_path, as_attachment=True, download_name=f'rapor_{current_user.kullanici_adi}.csv')
    except Exception as e:
        flash(f'CSV oluşturulurken hata oluştu: {str(e)}', 'error')
        return redirect(url_for('reports'))

@app.route('/dil-secimi', methods=['GET', 'POST'])
@login_required
def dil_secimi():
    """
    Kullanıcının hedef dil ve seviyesini seçmesini sağlar.
    """
    if request.method == 'POST':
        hedef_dil = request.form.get('hedef_dil')
        seviye = request.form.get('seviye')
        if hedef_dil and seviye:
            if update_user_language(current_user.id, hedef_dil, seviye):
                flash('Hedef diliniz ve seviyeniz başarıyla kaydedildi!', 'success')
                return redirect(url_for('home'))
            else:
                flash('Bir hata oluştu!', 'error')
        else:
            flash('Lütfen hem dil hem de seviye seçin!', 'error')
        return redirect(url_for('dil_secimi'))
    
    return render_template('language_selection.html')

@app.route('/home')
@login_required
def home():
    """
    Kullanıcının ana sayfası. İlerleme, tamamlanan bölümler ve günlük görevleri gösterir.
    """
    # Kullanıcı ilerlemesini al
    ilerleme = get_user_progress_data(current_user.id)
    
    # Günlük görevleri al
    görevler = get_daily_tasks(current_user.id)
    
    return render_template('home.html', 
                         ilerleme=ilerleme,
                         görevler=görevler)

@app.route('/tasks')
@login_required
def tasks():
    return render_template('tasks.html')

@app.route('/greeting', methods=['GET', 'POST'])
@login_required
def greeting_redirect():
    return redirect(url_for('greeting_test', test_no=1))

@app.route('/greeting/<int:test_no>', methods=['GET', 'POST'])
@login_required
def greeting_test(test_no):
    if test_no < 1 or test_no > 5:
        abort(404)
    # Zorluk seviyesine göre prompt ayarla - yiyecek/içecek içermeyen selamlaşma ifadeleri
    difficulty_map = {
        1: 'kolay, temel selamlaşma ifadeleri (yiyecek/içecek konuları hariç)',
        2: 'biraz daha zor, günlük konuşmada geçen selamlaşmalar (yiyecek/içecek konuları hariç)',
        3: 'orta seviye, farklı bağlamlarda selamlaşma ve tanışma (yiyecek/içecek konuları hariç)',
        4: 'ileri seviye, deyimsel ve resmi selamlaşmalar (yiyecek/içecek konuları hariç)',
        5: 'çok zor, nadir kullanılan veya kültürel selamlaşma ifadeleri (yiyecek/içecek konuları hariç)'
    }
    difficulty = difficulty_map.get(test_no, 'kolay')
    prompt_topic = f"selamlaşma ve tanışma ifadeleri ({difficulty}) - yiyecek, içecek, yemek, restoran konuları hariç"
    if request.method == 'POST':
        skor = request.form.get('skor')
        if skor:
            try:
                skor = int(skor)
                ilerleme = get_user_progress_data(current_user.id)
                if ilerleme:
                    ilerleme.toplam_xp += skor
                    db.session.commit()
                    flash('Test tamamlandı!', 'success')
                    return redirect(url_for('home'))
            except (ValueError, json.JSONDecodeError):
                flash('Bir hata oluştu. Lütfen tekrar deneyin.', 'error')
                return redirect(url_for('greeting_test', test_no=test_no))
    sorular = None
    try:
        sorular = generate_gemini_mc_questions(prompt_topic, num_questions=10, language='en')
    except Exception as e:
        print(f"Gemini API ile soru alınamadı: {e}")
        sorular = []
    random.shuffle(sorular)
    return render_template('greeting.html', sorular=sorular, test_no=test_no)



@app.route('/quiz')
@login_required
def quiz():
    topic = request.args.get('topic')
    return render_template('quiz.html', topic=topic)

@app.route('/quiz/yemek/<int:test_no>', methods=['GET', 'POST'])
@login_required
def quiz_food_test(test_no):
    if test_no < 1 or test_no > 5:
        abort(404)
    difficulty_map = {
        1: 'kolay, temel yemek isimleri',
        2: 'biraz daha zor, günlük yemek konuşmaları',
        3: 'orta seviye, yemek tarifleri ve restoran diyalogları',
        4: 'ileri seviye, deyimsel ve kültürel yemek ifadeleri',
        5: 'çok zor, nadir kullanılan veya bölgesel yemekler'
    }
    difficulty = difficulty_map.get(test_no, 'kolay')
    prompt_topic = f"yemekler ({difficulty})"
    if request.method == 'POST':
        skor = request.form.get('skor')
        if skor:
            try:
                skor = int(skor)
                ilerleme = get_user_progress_data(current_user.id)
                if ilerleme:
                    ilerleme.toplam_xp += skor
                    db.session.commit()
                    flash('Test tamamlandı!', 'success')
                    return redirect(url_for('home'))
            except (ValueError, json.JSONDecodeError):
                flash('Bir hata oluştu. Lütfen tekrar deneyin.', 'error')
                return redirect(url_for('quiz_food_test', test_no=test_no))
    sorular = None
    try:
        sorular = generate_gemini_mc_questions(prompt_topic, num_questions=10, language='en')
    except Exception as e:
        print(f"Gemini API ile soru alınamadı: {e}")
        sorular = []
    random.shuffle(sorular)
    return render_template('greeting.html', sorular=sorular, test_no=test_no, food_mode=True)

@app.route('/chatbot', methods=['GET', 'POST'])
@login_required
def chatbot():
    if 'chat_history' not in session:
        session['chat_history'] = []
        session['chat_start_time'] = datetime.utcnow().timestamp()
        # Clear old analysis results when starting new chat
        session.pop('chatbot_analysis', None)
        # Add initial bot message
        import random
        initial_messages = [
            "Hi! I'm your English friend. How are you?",
            "Hello! I'm here to talk with you. How are you today?",
            "Hey! I'm your chat friend. How is your day?",
            "Hi! I'm happy to talk with you. What do you want to talk about?",
            "Hello! I'm here to help you. How do you feel today?"
        ]
        session['chat_history'].append({
            'role': 'bot', 
            'text': random.choice(initial_messages)
        })
    
    chat_history = session['chat_history']
    chat_start_time = session.get('chat_start_time', datetime.utcnow().timestamp())
    completed = False
    gpt_feedback = None
    time_remaining = 180 # 3 minutes in seconds
    
    # Calculate remaining time
    elapsed_time = datetime.utcnow().timestamp() - chat_start_time
    time_remaining = max(0, 180 - int(elapsed_time))
    
    if request.method == 'POST':
        user_message = request.form.get('user_message', '').strip()
        if user_message and time_remaining > 0:
            chat_history.append({'role': 'user', 'text': user_message})
            
            # Enhanced bot response with context
            conversation_context = ""
            if len(chat_history) > 2:
                # Tüm konuşma geçmişini kullan (son kullanıcı mesajı hariç)
                conversation_context = "\n".join([
                    f"{'User' if msg['role']=='user' else 'Bot'}: {msg['text']}" 
                    for msg in chat_history[:-1]  # Son kullanıcı mesajını hariç tut
                ])
            
            bot_reply = generate_chatbot_response(user_message, conversation_context, "general")
            
            chat_history.append({'role': 'bot', 'text': bot_reply})
            session['chat_history'] = chat_history
            
        # Check if time is up
        user_msgs = [m for m in chat_history if m['role']=='user']
        time_is_up = time_remaining <= 0
        
        print(f"🔍 DEBUG: time_remaining={time_remaining}, time_is_up={time_is_up}")
        print(f"🔍 DEBUG: chatbot_checked={session.get('chatbot_checked')}")
        print(f"🔍 DEBUG: user_msgs_count={len(user_msgs)}")
        
        if time_is_up:
            print("🔍 Sohbet tamamlandı, değerlendirme başlatılıyor...")
            print(f"🔍 time_is_up: {time_is_up}")
            print(f"🔍 chatbot_checked: {session.get('chatbot_checked')}")
            print(f"🔍 user_msgs sayısı: {len(user_msgs)}")
            
            # Evaluate the conversation
            conversation = '\n'.join([f"User: {m['text']}" if m['role']=='user' else f"Bot: {m['text']}" for m in chat_history])
            
            # Basit değerlendirme kriterleri
            try:
                # Basit kriterler: mesaj sayısı ve uzunluk
                total_user_text = sum(len(m['text']) for m in user_msgs)
                avg_length = total_user_text / len(user_msgs) if user_msgs else 0
                
                # Daha esnek kriterler
                if len(user_msgs) >= 2 and avg_length >= 5:  # Daha düşük eşik
                    completed = True
                    session['chatbot_checked'] = True
                    gpt_feedback = "EVET"
                else:
                    gpt_feedback = "HAYIR"
                    
            except Exception as e:
                print(f"❌ Değerlendirme hatası: {e}")
                # En basit fallback
                if len(user_msgs) >= 1:
                    completed = True
                    session['chatbot_checked'] = True
                    gpt_feedback = "EVET"
                else:
                    gpt_feedback = "HAYIR"
    else:
        session.pop('chatbot_checked', None)
    
    return render_template('chatbot.html', 
                         chat_history=chat_history, 
                         completed=completed, 
                         gpt_feedback=gpt_feedback,
                         time_remaining=time_remaining)

@app.route('/chatbot/analysis')
@login_required
def chatbot_analysis():
    """Chatbot analiz sonuçlarını göster"""
    # Önce session'dan analiz ID'sini al
    analiz_id = session.get('chatbot_analysis_id')
    
    if analiz_id:
        # Veritabanından analiz sonuçlarını getir
        analysis, success, message = get_chatbot_analysis(analiz_id)
        if success:
            return render_template('chatbot_analysis.html', analysis=analysis)
        else:
            print(f"❌ Analiz getirilirken hata: {message}")
            flash('Analiz sonuçları bulunamadı!', 'error')
    else:
        # Session'da ID yoksa kullanıcının en son analizini getir
        latest_analysis, success, message = get_user_latest_analysis(current_user.id)
        if success:
            session['chatbot_analysis_id'] = latest_analysis['id']
            return render_template('chatbot_analysis.html', analysis=latest_analysis)
        else:
            print(f"❌ En son analiz getirilirken hata: {message}")
            flash('Henüz bir analiz yapılmamış!', 'info')
    
    return render_template('chatbot_analysis.html', analysis=None)

@app.route('/chatbot/analyze', methods=['POST'])
@login_required
def analyze_chatbot():
    """Chatbot sohbetini analiz et"""
    if 'chat_history' not in session:
        flash('Sohbet geçmişi bulunamadı!', 'error')
        return redirect(url_for('chatbot'))
    
    chat_history = session['chat_history']
    
    try:
        print("🔍 AI analizi başlatılıyor...")
        analysis_results = analyze_chatbot_conversation(chat_history)
        
        # Analiz sonuçlarını veritabanına kaydet
        analiz_id, success, message = save_chatbot_analysis(
            current_user.id, 'general', analysis_results
        )
        
        if success:
            session['chatbot_analysis_id'] = analiz_id
            print(f"✅ AI analizi tamamlandı ve veritabanına kaydedildi (ID: {analiz_id})")
            flash('Analiz tamamlandı!', 'success')
        else:
            print(f"❌ Analiz kaydedilirken hata: {message}")
            flash('Analiz tamamlandı ama kaydedilirken hata oluştu!', 'warning')
            
    except Exception as analysis_error:
        print(f"❌ AI analizi hatası: {analysis_error}")
        # Basit fallback analizi
        fallback_analysis = {
            'vocabulary': 'Analiz yapılamadı. Daha fazla mesaj göndermeyi deneyin.',
            'grammar': 'Analiz yapılamadı. Daha fazla mesaj göndermeyi deneyin.',
            'pronunciation': 'Analiz yapılamadı. Daha fazla mesaj göndermeyi deneyin.',
            'alternatives': 'Analiz yapılamadı. Daha fazla mesaj göndermeyi deneyin.',
            'fluency': 'Analiz yapılamadı. Daha fazla mesaj göndermeyi deneyin.',
            'communication': 'Analiz yapılamadı. Daha fazla mesaj göndermeyi deneyin.',
            'recommendations': 'Analiz yapılamadı. Daha fazla mesaj göndermeyi deneyin.'
        }
        
        analiz_id, success, message = save_chatbot_analysis(
            current_user.id, 'general', fallback_analysis
        )
        
        if success:
            session['chatbot_analysis_id'] = analiz_id
            print("✅ Fallback analiz veritabanına kaydedildi")
        else:
            print(f"❌ Fallback analiz kaydedilirken hata: {message}")
        
        flash('Analiz tamamlandı!', 'success')
    
    return redirect(url_for('chatbot_analysis'))

@app.route('/chatbot/yemek', methods=['GET', 'POST'])
@login_required
def chatbot_food():
    if 'chat_history_food' not in session:
        session['chat_history_food'] = []
        session['chat_food_start_time'] = datetime.utcnow().timestamp()
        # Clear old analysis results when starting new chat
        session.pop('chatbot_analysis', None)
        # Add initial bot message for food conversation
        import random
        food_initial_messages = [
            "Hello! Welcome to our restaurant. What would you like to order today?",
            "Hi there! I'm your waiter. What can I get for you?",
            "Good day! Welcome to our restaurant. What would you like to eat?",
            "Hello! I'm here to take your order. What would you like?",
            "Hi! Welcome to our restaurant. What can I help you with today?"
        ]
        session['chat_history_food'].append({
            'role': 'bot', 
            'text': random.choice(food_initial_messages)
        })
    
    chat_history = session['chat_history_food']
    chat_start_time = session.get('chat_food_start_time', datetime.utcnow().timestamp())
    completed = False
    gpt_feedback = None
    time_remaining = 180  # 3 minutes in seconds
    
    # Calculate remaining time
    elapsed_time = datetime.utcnow().timestamp() - chat_start_time
    time_remaining = max(0, 180 - int(elapsed_time))
    
    if request.method == 'POST':
        user_message = request.form.get('user_message', '').strip()
        if user_message and time_remaining > 0:
            chat_history.append({'role': 'user', 'text': user_message})
            
            # Enhanced bot response with food context
            conversation_context = ""
            if len(chat_history) > 2:
                # Tüm konuşma geçmişini kullan (son kullanıcı mesajı hariç)
                conversation_context = "\n".join([
                    f"{'User' if msg['role']=='user' else 'Bot'}: {msg['text']}" 
                    for msg in chat_history[:-1]  # Son kullanıcı mesajını hariç tut
                ])
            
            bot_reply = generate_chatbot_response(user_message, conversation_context, "food")
            
            chat_history.append({'role': 'bot', 'text': bot_reply})
            session['chat_history_food'] = chat_history
            
        # Check if time is up
        user_msgs = [m for m in chat_history if m['role']=='user']
        time_is_up = time_remaining <= 0
        
        print(f"🔍 DEBUG FOOD: time_remaining={time_remaining}, time_is_up={time_is_up}")
        print(f"🔍 DEBUG FOOD: chatbot_food_checked={session.get('chatbot_food_checked')}")
        print(f"🔍 DEBUG FOOD: user_msgs_count={len(user_msgs)}")
        
        if time_is_up:
            print("🔍 Food sohbeti tamamlandı, değerlendirme başlatılıyor...")
            print(f"🔍 time_is_up: {time_is_up}")
            print(f"🔍 chatbot_food_checked: {session.get('chatbot_food_checked')}")
            print(f"🔍 user_msgs sayısı: {len(user_msgs)}")
            # Evaluate the conversation
            conversation = '\n'.join([f"User: {m['text']}" if m['role']=='user' else f"Bot: {m['text']}" for m in chat_history])
            
            # Basit değerlendirme kriterleri (restoran için)
            try:
                # Basit kriterler: mesaj sayısı ve uzunluk
                total_user_text = sum(len(m['text']) for m in user_msgs)
                avg_length = total_user_text / len(user_msgs) if user_msgs else 0
                
                # Daha esnek kriterler
                if len(user_msgs) >= 2 and avg_length >= 5:  # Daha düşük eşik
                    completed = True
                    session['chatbot_food_checked'] = True
                    gpt_feedback = "EVET"
                else:
                    gpt_feedback = "HAYIR"
                    
            except Exception as e:
                print(f"❌ Food değerlendirme hatası: {e}")
                # En basit fallback
                if len(user_msgs) >= 1:
                    completed = True
                    session['chatbot_food_checked'] = True
                    gpt_feedback = "EVET"
                else:
                    gpt_feedback = "HAYIR"
    else:
        session.pop('chatbot_food_checked', None)
    
    return render_template('chatbot.html', 
                         chat_history=chat_history, 
                         completed=completed, 
                         gpt_feedback=gpt_feedback,
                         time_remaining=time_remaining,
                         food_mode=True)

@app.route('/chatbot/food/analyze', methods=['POST'])
@login_required
def analyze_chatbot_food():
    """Food chatbot sohbetini analiz et"""
    if 'chat_history_food' not in session:
        flash('Sohbet geçmişi bulunamadı!', 'error')
        return redirect(url_for('chatbot_food'))
    
    chat_history = session['chat_history_food']
    
    try:
        print("🔍 Food AI analizi başlatılıyor...")
        analysis_results = analyze_chatbot_conversation(chat_history)
        
        # Analiz sonuçlarını veritabanına kaydet
        analiz_id, success, message = save_chatbot_analysis(
            current_user.id, 'food', analysis_results
        )
        
        if success:
            session['chatbot_analysis_id'] = analiz_id
            print(f"✅ Food AI analizi tamamlandı ve veritabanına kaydedildi (ID: {analiz_id})")
            flash('Analiz tamamlandı!', 'success')
        else:
            print(f"❌ Food analiz kaydedilirken hata: {message}")
            flash('Analiz tamamlandı ama kaydedilirken hata oluştu!', 'warning')
            
    except Exception as analysis_error:
        print(f"❌ Food AI analizi hatası: {analysis_error}")
        # Basit fallback analizi
        fallback_analysis = {
            'vocabulary': 'Analiz yapılamadı. Daha fazla mesaj göndermeyi deneyin.',
            'grammar': 'Analiz yapılamadı. Daha fazla mesaj göndermeyi deneyin.',
            'pronunciation': 'Analiz yapılamadı. Daha fazla mesaj göndermeyi deneyin.',
            'alternatives': 'Analiz yapılamadı. Daha fazla mesaj göndermeyi deneyin.',
            'fluency': 'Analiz yapılamadı. Daha fazla mesaj göndermeyi deneyin.',
            'communication': 'Analiz yapılamadı. Daha fazla mesaj göndermeyi deneyin.',
            'recommendations': 'Analiz yapılamadı. Daha fazla mesaj göndermeyi deneyin.'
        }
        
        analiz_id, success, message = save_chatbot_analysis(
            current_user.id, 'food', fallback_analysis
        )
        
        if success:
            session['chatbot_analysis_id'] = analiz_id
            print("✅ Food fallback analiz veritabanına kaydedildi")
        else:
            print(f"❌ Food fallback analiz kaydedilirken hata: {message}")
        
        flash('Analiz tamamlandı!', 'success')
    
    return redirect(url_for('chatbot_analysis'))

with app.app_context():
    admin_kullanici_olustur()

if __name__ == '__main__':
    app.run(debug=True) 
    