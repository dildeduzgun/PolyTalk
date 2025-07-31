// Smooth scrolling for anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        document.querySelector(this.getAttribute('href')).scrollIntoView({
            behavior: 'smooth'
        });
    });
});

// Animate elements when they come into view
const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('animate');
        }
    });
}, { threshold: 0.1 });

document.querySelectorAll('.feature-card, .step, .dashboard-card').forEach(el => {
    observer.observe(el);
});

// Flash message auto-dismiss
document.querySelectorAll('.flash-message').forEach(message => {
    setTimeout(() => {
        message.style.opacity = '0';
        setTimeout(() => message.remove(), 300);
    }, 3000);
});

// Form validation
document.querySelectorAll('form').forEach(form => {
    form.addEventListener('submit', function(e) {
        const requiredFields = form.querySelectorAll('[required]');
        let isValid = true;

        requiredFields.forEach(field => {
            if (!field.value.trim()) {
                isValid = false;
                field.classList.add('error');
            } else {
                field.classList.remove('error');
            }
        });

        if (!isValid) {
            e.preventDefault();
            alert('Lütfen tüm gerekli alanları doldurun.');
        }
    });
});

// Password strength indicator
const passwordInput = document.querySelector('input[type="password"]');
if (passwordInput) {
    passwordInput.addEventListener('input', function() {
        const password = this.value;
        let strength = 0;

        if (password.length >= 8) strength++;
        if (password.match(/[a-z]/)) strength++;
        if (password.match(/[A-Z]/)) strength++;
        if (password.match(/[0-9]/)) strength++;
        if (password.match(/[^a-zA-Z0-9]/)) strength++;

        const strengthIndicator = document.createElement('div');
        strengthIndicator.className = 'password-strength';
        strengthIndicator.style.width = `${(strength / 5) * 100}%`;
        strengthIndicator.style.backgroundColor = strength < 3 ? '#ff4b4b' : 
                                               strength < 4 ? '#ffa500' : 
                                               '#58cc02';

        const existingIndicator = this.parentElement.querySelector('.password-strength');
        if (existingIndicator) {
            existingIndicator.remove();
        }
        this.parentElement.appendChild(strengthIndicator);
    });
}

// Card flip animation
document.querySelectorAll('.card').forEach(card => {
    card.addEventListener('click', function() {
        this.classList.toggle('flipped');
    });
});

// Test timer
let testTimer;
function startTestTimer(duration) {
    let timer = duration;
    const timerDisplay = document.querySelector('.test-timer');
    
    if (timerDisplay) {
        testTimer = setInterval(() => {
            const minutes = parseInt(timer / 60, 10);
            const seconds = parseInt(timer % 60, 10);

            timerDisplay.textContent = `${minutes}:${seconds < 10 ? '0' : ''}${seconds}`;

            if (--timer < 0) {
                clearInterval(testTimer);
                document.querySelector('.test-form').submit();
            }
        }, 1000);
    }
}

// Progress bar animation
function updateProgress(progress) {
    const progressBar = document.querySelector('.progress-bar');
    if (progressBar) {
        progressBar.style.width = `${progress}%`;
    }
}

// Mobile menu toggle
const menuToggle = document.querySelector('.menu-toggle');
const mobileMenu = document.querySelector('.mobile-menu');

if (menuToggle && mobileMenu) {
    menuToggle.addEventListener('click', () => {
        mobileMenu.classList.toggle('active');
    });
}

// Mini Test Handler
document.addEventListener('DOMContentLoaded', function() {
    const testSlider = document.querySelector('.test-slider');
    const slides = document.querySelectorAll('.test-slide');
    const prevButton = document.getElementById('prevQuestion');
    const nextButton = document.getElementById('nextQuestion');
    const progressFill = document.querySelector('.progress-fill');
    const questionCounter = document.querySelector('.question-counter');
    const resultModal = document.getElementById('testResultModal');

    if (testSlider) {
        let currentQuestion = 1;
        const totalQuestions = slides.length;
        const answers = {
            q1: 'a', // Merhaba
            q2: 'b', // Günaydın
            q3: 'b', // Teşekkür ederim
            q4: 'b', // Nasılsın?
            q5: 'b'  // Hoşça kal
        };

        // İlk soruyu göster
        showQuestion(currentQuestion);

        // Önceki soru butonu
        prevButton.addEventListener('click', () => {
            if (currentQuestion > 1) {
                currentQuestion--;
                showQuestion(currentQuestion);
            }
        });

        // Sonraki soru butonu
        nextButton.addEventListener('click', () => {
            const currentSlide = document.querySelector(`.test-slide[data-question="${currentQuestion}"]`);
            const selected = currentSlide.querySelector('input[type="radio"]:checked');
            
            if (!selected) {
                alert('Lütfen bir cevap seçin!');
                return;
            }

            // Cevabı kontrol et
            const isCorrect = selected.value === answers[`q${currentQuestion}`];
            showFeedback(currentSlide, isCorrect);

            // 1 saniye sonra sonraki soruya geç veya sonucu göster
            setTimeout(() => {
                if (currentQuestion < totalQuestions) {
                    currentQuestion++;
                    showQuestion(currentQuestion);
                } else if (currentQuestion === totalQuestions) {
                    // Son sorudayız, sonucu göster
                    const score = calculateScore();
                    showFinalScore(score);
                }
            }, 1000);
        });

        function showQuestion(questionNumber) {
            // Tüm soruları gizle
            slides.forEach(slide => {
                slide.classList.remove('active');
                slide.style.display = 'none';
                slide.querySelector('.feedback')?.remove();
            });

            // Seçili soruyu göster
            const currentSlide = document.querySelector(`.test-slide[data-question="${questionNumber}"]`);
            currentSlide.classList.add('active');
            currentSlide.style.display = 'block';

            // İlerleme çubuğunu güncelle
            const progress = ((questionNumber - 1) / totalQuestions) * 100;
            progressFill.style.width = `${progress}%`;
            questionCounter.textContent = `Soru ${questionNumber}/${totalQuestions}`;

            // Butonları güncelle
            prevButton.disabled = questionNumber === 1;
            nextButton.textContent = questionNumber === totalQuestions ? 'Bitir' : 'Sonraki';
        }

        function showFeedback(slide, isCorrect) {
            const feedback = document.createElement('div');
            feedback.className = `feedback ${isCorrect ? 'correct' : 'incorrect'}`;
            feedback.textContent = isCorrect ? 'Doğru!' : 'Yanlış!';
            slide.appendChild(feedback);
        }

        function calculateScore() {
            let score = 0;
            slides.forEach((slide, index) => {
                const selected = slide.querySelector('input[type="radio"]:checked');
                if (selected && selected.value === answers[`q${index + 1}`]) {
                    score++;
                }
            });
            return score;
        }

        // Test Sonuç Kutusu için referanslar
        const testResultBox = document.getElementById('testResultBox');
        const resultScoreNumber = testResultBox?.querySelector('.score-number');
        const resultAnswersList = testResultBox?.querySelector('.result-answers-list');
        const testSliderContainer = document.querySelector('.test-slider');
        const testNavigation = document.querySelector('.test-navigation');

        function showFinalScore(score) {
            const percentage = (score / totalQuestions) * 100;
            // Skor yaz
            if(resultScoreNumber) resultScoreNumber.textContent = score;

            // Soru ve cevapları hazırla
            const answerTexts = [
                {
                    q: '1. "Hello" kelimesinin Türkçe karşılığı nedir?',
                    correct: 'Merhaba',
                    options: { a: 'Merhaba', b: 'Hoşça kal', c: 'Nasılsın' }
                },
                {
                    q: '2. "Good morning" ne anlama gelir?',
                    correct: 'Günaydın',
                    options: { a: 'İyi akşamlar', b: 'Günaydın', c: 'İyi geceler' }
                },
                {
                    q: '3. "Thank you" ifadesinin Türkçe karşılığı nedir?',
                    correct: 'Teşekkür ederim',
                    options: { a: 'Lütfen', b: 'Teşekkür ederim', c: 'Rica ederim' }
                },
                {
                    q: '4. "How are you?" sorusunun anlamı nedir?',
                    correct: 'Nasılsın?',
                    options: { a: 'Adın ne?', b: 'Nasılsın?', c: 'Neredesin?' }
                },
                {
                    q: '5. "Goodbye" kelimesinin Türkçe karşılığı nedir?',
                    correct: 'Hoşça kal',
                    options: { a: 'Merhaba', b: 'Hoşça kal', c: 'Günaydın' }
                }
            ];
            let html = '';
            slides.forEach((slide, idx) => {
                const selected = slide.querySelector('input[type="radio"]:checked');
                const userVal = selected ? selected.value : null;
                const userText = userVal ? answerTexts[idx].options[userVal] : 'Cevap verilmedi';
                const isCorrect = userVal === Object.keys(answerTexts[idx].options).find(k=>answerTexts[idx].options[k]===answerTexts[idx].correct);
                html += `<div class="result-answer-item ${isCorrect ? 'correct' : 'incorrect'}">
                    <div class="result-answer-q">${answerTexts[idx].q}</div>
                    <div class="result-answer-user">Senin cevabın: <b>${userText}</b></div>
                    <div class="result-answer-correct">Doğru cevap: <b>${answerTexts[idx].correct}</b></div>
                </div>`;
            });
            if(resultAnswersList) resultAnswersList.innerHTML = html;

            // Slider ve navigation'ı gizle, sonucu göster
            if(testSliderContainer) testSliderContainer.style.display = 'none';
            if(testNavigation) testNavigation.style.display = 'none';
            if(testResultBox) testResultBox.style.display = 'flex';
        }
    }
}); 