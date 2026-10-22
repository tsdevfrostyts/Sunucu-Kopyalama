# Sunucu Kopyalama

Windows için açık kaynak, animasyonlu Discord sunucu yapısı kopyalama uygulaması.

**[v1.0.0 EXE indir](https://github.com/tsdevfrostyts/Sunucu-Kopyalama/releases/download/v1.0.0/Sunucu-Kopyalama_v1.0.0.exe)** · [Tüm sürümler](https://github.com/tsdevfrostyts/Sunucu-Kopyalama/releases)

## Gizlilik

Uygulama tamamen bilgisayarınızda çalışır. Geliştiriciye hiçbir bilgi veya telemetri göndermez; analiz, reklam veya harici veri toplama servisi içermez. İşlemleri gerçekleştirmek için internet üzerinden **doğrudan Discord API’sine** bağlanır; kullanıcı token’i yalnızca bu API’ye gönderilir.

Token uygulama tarafından diske veya işlem günlüğüne yazılmaz. Önizleme, hata ve iptal sonrasında tekrar denemek için bellekte tutulur; kopyalama doğrulanarak tamamlandığında veya uygulama kapatıldığında temizlenir. Kaynak/hedef sunucu yapıları yerel JSON yedeğine yazılır; bu dosyalar sunucu/rol/kanal kimlikleri ve izin bilgileri içerir. Yedekleri paylaşmadan önce inceleyin.

## Kapsam

- Roller: isim ve ana renk.
- Kategoriler ve kanallar: isim, sıralama, kategori ilişkisi ve rollere göre kanal izinleri.
- Ses kanalları ses, forum kanalları forum olarak oluşturulur. Forum etiketleri ve ek ayarlar kopyalanmaz.
- Duyuru ve medya kanalları normal metin; sahne kanalları normal ses kanalına dönüştürülür.
- Mesajlar, üyeler, üyelere özel izinler, genel rol yetkileri, emojiler ve sunucu ayarları kopyalanmaz. Kural/moderasyon kanalı atanmaz.

Forum oluşturma Discord’un hedef sunucudaki özellik ve API kısıtlarına bağlıdır; uygulama bunları aşmaz.

## Kullanım

1. EXE dosyasını açın. Python kurulumu gerekmez.
2. Kendi hesabınızın kullanıcı token’ini ve kaynak/hedef sunucu ID’lerini girin.
3. Önizlemeyi inceleyip kopyalamayı başlatın. Hedef sunucunun sahibi veya Yönetici yetkili olmalısınız; kaynak yapıya erişiminiz bulunmalıdır.
4. İlerlemeyi işlem günlüğünden takip edin. Silinemeyen roller/kanallar isim ve ID ile kırmızı gösterilir; işlem devam eder.

**Kopyalama hedefte mevcut rol ve kanalları silmeye çalışır. Kanal silinmesi içindeki mesajları da kaybettirebilir. İkinci onay penceresi yoktur; hedef ID’sini önizlemede kontrol edin.** Yerel yedek yalnızca yapı kaydıdır; otomatik geri yükleme ve mesaj kurtarma sağlamaz. İptal/hata tamamlanmış işlemleri geri almaz.

Yapı yedekleri `%LOCALAPPDATA%\SunucuKopyalayici\backups` altında tutulur; arayüzdeki düğmeyle açılabilir.

Kullanıcı hesabı otomasyonu Discord kurallarına aykırı olabilir ve hesabınızın kısıtlanmasına yol açabilir. Yalnızca kendi hesabınızla ve yönetmeye yetkili olduğunuz sunucularda kullanın. Token’inizi kimseyle paylaşmayın.

## Kaynaktan çalıştırma ve EXE oluşturma

Windows, Python 3.14 ve PowerShell ile:

```powershell
.\build.ps1
```

Bu komut sanal ortamı/bağımlılıkları hazırlar, testleri çalıştırır, `dist/Sunucu-Kopyalama_v1.0.0.exe` üretir ve paketlenmiş arayüzün öz denetimini çalıştırır. Derleme bağımlılıklarının kurulumu paket kayıt sistemlerine bağlanır; bu, son kullanıcının EXE çalışma akışından ayrıdır.

Kaynaktan açmak için:

```powershell
.\.venv\Scripts\python.exe app.py
```

## Doğrulama

v1.0.0 için 43 otomatik test (31 çekirdek/aktarım, 12 arayüz) ve üretilen EXE’nin arayüz öz denetimi geçti. Ağ testleri taklit yanıtlarla çalışır. Önceki çalışan çekirdeğin gerçek kopyalama işlemini kullanıcı doğruladı; bu sürümdeki görsel değişiklikler sonrasında tüm canlı Discord senaryoları ayrıca denenmedi. EXE dijital olarak imzalanmamıştır. İndirilen dosyanın SHA256 özeti sürümdeki `SHA256SUMS.txt` ile karşılaştırılabilir.

## Lisans

[MIT](LICENSE). CustomTkinter arayüzü/simgesi ve diğer bileşenlerin lisansları [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) dosyasındadır. Discord ile bağlantılı veya Discord tarafından onaylanmış bir ürün değildir.
