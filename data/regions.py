"""O'zbekiston viloyatlari va ulardagi tuman/shaharlar ro'yxati."""

REGIONS: list[dict] = [
    {
        "name": "Toshkent shahri",
        "districts": [
            "Bektemir", "Chilonzor", "Mirobod", "Mirzo Ulug'bek",
            "Olmazor", "Sergeli", "Shayxontohur", "Uchtepa",
            "Yakkasaroy", "Yangihayot", "Yashnobod", "Yunusobod",
        ],
    },
    {
        "name": "Toshkent viloyati",
        "districts": [
            "Nurafshon", "Angren", "Bekobod shahri", "Bekobod tumani",
            "Bo'ka", "Bo'stonliq", "Chinoz", "Ohangaron shahri",
            "Ohangaron tumani", "Olmaliq", "Oqqo'rg'on", "O'rtachirchiq",
            "Parkent", "Piskent", "Qibray", "Quyichirchiq",
            "Yangiyo'l shahri", "Yangiyo'l tumani", "Yuqorichirchiq", "Zangiota",
        ],
    },
    {
        "name": "Andijon viloyati",
        "districts": [
            "Andijon shahri", "Andijon tumani", "Asaka", "Baliqchi",
            "Bo'ston", "Buloqboshi", "Izboskan", "Jalaquduq",
            "Marhamat", "Oltinko'l", "Paxtaobod", "Qo'rg'ontepa",
            "Shahrixon", "Ulug'nor", "Xonobod", "Xo'jaobod",
        ],
    },
    {
        "name": "Buxoro viloyati",
        "districts": [
            "Buxoro shahri", "Buxoro tumani", "G'ijduvon", "Jondor",
            "Kogon shahri", "Kogon tumani", "Olot", "Peshku",
            "Qorako'l", "Qorovulbozor", "Romitan", "Shofirkon",
            "Vobkent",
        ],
    },
    {
        "name": "Farg'ona viloyati",
        "districts": [
            "Farg'ona shahri", "Marg'ilon", "Qo'qon", "Quvasoy",
            "Beshariq", "Bog'dod", "Buvayda", "Dang'ara",
            "Furqat", "Oltiariq", "O'zbekiston", "Qo'shtepa",
            "Quva", "Rishton", "So'x", "Toshloq",
            "Uchko'prik", "Yozyovon",
        ],
    },
    {
        "name": "Jizzax viloyati",
        "districts": [
            "Jizzax shahri", "Arnasoy", "Baxmal", "Do'stlik",
            "Forish", "G'allaorol", "Mirzacho'l", "Paxtakor",
            "Sharof Rashidov", "Yangiobod", "Zafarobod", "Zarbdor",
            "Zomin",
        ],
    },
    {
        "name": "Xorazm viloyati",
        "districts": [
            "Urganch shahri", "Urganch tumani", "Xiva shahri", "Xiva tumani",
            "Bog'ot", "Gurlan", "Hazorasp", "Xonqa",
            "Qo'shko'pir", "Shovot", "Yangiariq", "Yangibozor",
            "Tuproqqal'a",
        ],
    },
    {
        "name": "Namangan viloyati",
        "districts": [
            "Namangan shahri", "Namangan tumani", "Chortoq", "Chust",
            "Kosonsoy", "Mingbuloq", "Norin", "Pop",
            "To'raqo'rg'on", "Uchqo'rg'on", "Uychi", "Yangiqo'rg'on",
        ],
    },
    {
        "name": "Navoiy viloyati",
        "districts": [
            "Navoiy shahri", "Zarafshon", "G'ozg'on", "Karmana",
            "Konimex", "Navbahor", "Nurota", "Qiziltepa",
            "Tomdi", "Uchquduq", "Xatirchi",
        ],
    },
    {
        "name": "Qashqadaryo viloyati",
        "districts": [
            "Qarshi shahri", "Qarshi tumani", "Shahrisabz shahri", "Shahrisabz tumani",
            "Chiroqchi", "Dehqonobod", "G'uzor", "Kasbi",
            "Kitob", "Koson", "Mirishkor", "Muborak",
            "Nishon", "Qamashi", "Yakkabog'",
        ],
    },
    {
        "name": "Qoraqalpog'iston Respublikasi",
        "districts": [
            "Nukus shahri", "Nukus tumani", "Taxiatosh", "Xo'jayli",
            "Amudaryo", "Beruniy", "Chimboy", "Ellikqal'a",
            "Kegeyli", "Mo'ynoq", "Qanliko'l", "Qo'ng'irot",
            "Qorao'zak", "Shumanay", "Taxtako'pir", "To'rtko'l",
        ],
    },
    {
        "name": "Samarqand viloyati",
        "districts": [
            "Samarqand shahri", "Samarqand tumani", "Kattaqo'rg'on shahri",
            "Kattaqo'rg'on tumani", "Bulung'ur", "Ishtixon", "Jomboy",
            "Nurobod", "Oqdaryo", "Past Dargom", "Paxtachi",
            "Payariq", "Qo'shrabot", "Toyloq", "Urgut",
        ],
    },
    {
        "name": "Sirdaryo viloyati",
        "districts": [
            "Guliston shahri", "Guliston tumani", "Shirin", "Yangiyer",
            "Boyovut", "Mirzaobod", "Oqoltin", "Sayxunobod",
            "Sardoba", "Sirdaryo", "Xovos",
        ],
    },
    {
        "name": "Surxondaryo viloyati",
        "districts": [
            "Termiz shahri", "Termiz tumani", "Denov", "Sho'rchi",
            "Angor", "Bandixon", "Boysun", "Jarqo'rg'on",
            "Muzrabot", "Oltinsoy", "Qiziriq", "Qumqo'rg'on",
            "Sariosiyo", "Sherobod", "Uzun",
        ],
    },
]


def get_region(idx: int) -> dict | None:
    if 0 <= idx < len(REGIONS):
        return REGIONS[idx]
    return None


def get_district(region_idx: int, district_idx: int) -> str | None:
    region = get_region(region_idx)
    if region and 0 <= district_idx < len(region["districts"]):
        return region["districts"][district_idx]
    return None
