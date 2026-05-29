"""Test foydalanuvchilar ro'yxati — /seed admin buyrug'i uchun.

Ular faqat qidiruv interfeysini sinash uchun. Bu user_id'lar real
Telegram foydalanuvchilarining ID'lariga to'g'ri kelmasligi uchun
9'dan boshlangan (Telegram diapazonidan yuqori).
"""

BASE_ID = 9_000_000_000

# Maydonlar: gender, name, age, looking_for, city, bio, latitude, longitude
TEST_USERS: list[tuple[str, str, int, str, str, str, float, float]] = [
    # Ayollar (8 ta)
    ("F", "Aziza", 22, "M", "Toshkent shahri, Yunusobod",
     "Sport bilan shug'ullanaman 🏃‍♀️", 41.36, 69.27),
    ("F", "Madina", 24, "M", "Toshkent shahri, Chilonzor",
     "Kitob o'qishni yaxshi ko'raman 📚", 41.28, 69.20),
    ("F", "Nilufar", 20, "M", "Samarqand viloyati, Samarqand shahri",
     "Talabaman, sayohatni sevaman", 39.65, 66.97),
    ("F", "Dilfuza", 26, "M", "Buxoro viloyati, Buxoro shahri",
     "Tarjimon. Italyan tilini o'rganyapman", 39.77, 64.42),
    ("F", "Shahnoza", 23, "M", "Andijon viloyati, Andijon shahri",
     "Musiqa ishqibozi 🎵", 40.78, 72.34),
    ("F", "Gulnora", 28, "M", "Toshkent shahri, Mirzo Ulug'bek",
     "IT sohasida ishlayman. Kofeshap'larni yaxshi ko'raman ☕", 41.32, 69.34),
    ("F", "Iroda", 21, "M", "Farg'ona viloyati, Marg'ilon",
     "O'qituvchi bo'lmoqchiman 📖", 40.47, 71.72),
    ("F", "Munisa", 25, "M", "Toshkent shahri, Yashnobod",
     "Yoga va meditatsiya, dengiz va tog' 🧘‍♀️", 41.30, 69.34),

    # Erkaklar (7 ta)
    ("M", "Sardor", 25, "F", "Toshkent shahri, Sergeli",
     "Dasturchiman 💻. Velosport ham yoqadi", 41.23, 69.20),
    ("M", "Jasur", 27, "F", "Toshkent shahri, Yunusobod",
     "Fitnes va sog'lom turmush tarzi 💪", 41.36, 69.27),
    ("M", "Bekzod", 23, "F", "Samarqand viloyati, Samarqand shahri",
     "Biznes talabasi, sayohatchi", 39.65, 66.97),
    ("M", "Akmal", 29, "F", "Toshkent viloyati, Yangiyo'l shahri",
     "Tibbiyot vakili. Bo'sh vaqtimda kitob o'qiyman", 41.11, 69.05),
    ("M", "Davron", 26, "F", "Namangan viloyati, Namangan shahri",
     "Muhandisman. Shaxmat va film ko'rishni sevaman 🎬", 40.99, 71.67),
    ("M", "Otabek", 22, "F", "Toshkent shahri, Chilonzor",
     "Yangi tanishlar izlayman 🙂", 41.28, 69.20),
    ("M", "Rustam", 30, "F", "Buxoro viloyati, Buxoro shahri",
     "Tarjimon. Rus va ingliz tilini bilaman", 39.77, 64.42),
]
