"""5 ta qiz test anketalari (16-19 yosh) — har biri unique rasm bilan.

Admin /seedgirls buyrug'i orqali ishlatiladi. Admin 5 ta rasm yuborganda
har bir rasm shu yerdagi mos anketaga yopishtiriladi.

ID range: 9_100_000_000 + 1..5 (mavjud TEST_USERS bilan to'qnashmaslik uchun)
"""

BASE_ID_GIRLS = 9_100_000_000

# (name, age, looking_for, city, bio, latitude, longitude)
TEST_GIRLS: list[tuple[str, int, str, str, str, float, float]] = [
    (
        "Sevinch", 18, "M",
        "Toshkent shahri, Chilonzor",
        "Universitet talabasi, IT yo'nalishi 💻",
        41.28, 69.20,
    ),
    (
        "Madina", 17, "M",
        "Samarqand viloyati, Samarqand shahri",
        "Kitob va sayohatni yoqtiraman ✈️",
        39.65, 66.97,
    ),
    (
        "Lola", 19, "M",
        "Buxoro viloyati, Buxoro shahri",
        "Tarjimon bo'lmoqchiman 🌍",
        39.77, 64.42,
    ),
    (
        "Diyora", 17, "M",
        "Andijon viloyati, Andijon shahri",
        "Musiqa va san'at ishqibozi 🎵",
        40.78, 72.34,
    ),
    (
        "Aziza", 19, "M",
        "Toshkent shahri, Yunusobod",
        "Sport va sog'lom turmush tarzi 🏃‍♀️",
        41.36, 69.27,
    ),
]
