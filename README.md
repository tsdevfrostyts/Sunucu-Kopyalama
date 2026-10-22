# Sunucu Kopyalama

Windows için animasyonlu Discord sunucu yapısı kopyalama uygulaması.

**[v1.0.1 EXE indir](https://github.com/tsdevfrostyts/Sunucu-Kopyalama/releases/download/v1.0.1/Sunucu-Kopyalama_v1.0.1.exe)** · [Tüm sürümler](https://github.com/tsdevfrostyts/Sunucu-Kopyalama/releases)

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

## Lisans

v1.0.1 ve sonraki yeni dağıtımlar [kapalı kaynak kullanım lisansına](LICENSE) tabidir. Uygulamayı ücretsiz indirip kullanabilirsiniz; uygulamanın mülkiyeti veya yeni kaynak kodu üzerinde hak devri yapılmaz. Önceden MIT lisansıyla yayımlanmış v1.0.0 kodu ve kopyaları için verilmiş haklar korunur; yeni lisans bunları geriye dönük kısıtlamaz.

Bu depo yeni sürümlerin indirme ve lisans bilgileri içindir; yeni uygulama kaynak kodu yayımlanmaz. Önceden yayımlanmış Git geçmişi ve v1.0.0 etiketi korunur. CustomTkinter arayüzü/simgesi ve diğer bileşenler kendi lisanslarına tabidir; metinleri [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) dosyasındadır. Discord ile bağlantılı veya Discord tarafından onaylanmış bir ürün değildir.
