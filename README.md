# Sunucu Kopyalama

Windows için açık kaynak, animasyonlu Discord sunucu yapısı kopyalama uygulaması.

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

## VirusTotal ve Windows uyarıları neden görülebilir?

Uygulama Python ile yazılır ve PyInstaller kullanılarak tek EXE olarak paketlenir. Açılışta gerekli Python/Tcl/Tk kitaplıkları, temalar ve fontlar Windows'un geçici klasöründeki `_MEI*` dizinine açılır; `python314.dll` uygulama sürecine yüklenir. Bu gerçek paketleme davranışı, genel “PE dosyası oluşturma” ve “Python olmayan süreçte Python yükleme” kurallarıyla eşleşebilir. `obfuscated` etiketi tek başına özel bir kod gizleme yöntemi kullanıldığını kanıtlamaz; bu projede ek obfuscator veya UPX kullanılmıyor. Gereksiz toplu paketleme kaldırıldı; 43 ham Python ve 7 paket metadata dosyası artık çalışma sırasında açılmıyor.

Kaynak incelemesinde uygulamanın kök sertifika eklediği, otomatik başlatma kurduğu veya geliştiriciye bilgi gönderdiği bir kod yolu bulunmadı. Eski sandbox raporundaki sertifika deposu uyarısının kesin süreç ve kayıt yolu erişilebilen özetten doğrulanamadı. Bu yüzden bu uyarıyı kesin olarak “yanlış alarm” diye kapatmıyoruz. Python'un işletim sistemi sürümü sorgusu da bazı ortamlarda `cmd /c ver` komutuna düşebilir; bu uygulamanın uzaktan komut aldığı anlamına gelmez.

**Antivirüs tespiti, dijital imza güveni ve SmartScreen itibarı ayrı değerlendirmelerdir.** Mevcut EXE kendinden imzalıdır; sertifikası bağımsız, Windows'un güvendiği bir otorite tarafından onaylanmamıştır. Bu nedenle “yayıncı doğrulanamadı” veya güvenilmeyen kök uyarısı görülebilir. Zaman damgası yayıncı kimliğini onaylamaz. Kullanıcı sayısının artması bu sertifikayı otomatik olarak güvenilir yapmaz. SmartScreen'in dosya/yayıncı itibarı zamanla değişebilir; belirli bir kullanıcı sayısında veya birkaç hafta içinde onay garantisi yoktur. [Microsoft'un açıklaması](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation).

Bir tarama sonucu uygulamanın bütünü için güvenlik garantisi değildir; açık kaynak olması veya imza bulunması da tek başına yeterli değildir. Kaynak kodunu ve [bu sürümdeki EXE'nin VirusTotal sonucunu](https://www.virustotal.com/gui/file/b9c54eead0fea243b368639011d29ff5e5dbafe5241ce958bf526e023d947737/detection) birlikte değerlendirebilirsiniz. Uyarıları gidermek için Windows/antivirüs korumalarını kapatmanız veya kök sertifika yüklemeniz istenmez.

22 Ekim 2026 tarihinde bu sürümün son EXE taraması **4/70** tespit bildirdi: Bkav Pro, Elastic, Microsoft (`Trojan:Win32/Wacatac.C!ml`) ve SecureAge. Aynı dosyanın yerel Defender taramasında tehdit bulunmadı; motor, bulut ve tanım farklılıkları nedeniyle sonuçlar değişebilir. Bu farklılık dört tespitin yanlış olduğunu kanıtlamaz. VirusTotal ayrıntılarındaki `invalid-signature` etiketinin açıklaması, imza zincirinin güvenilmeyen bir kökte sonlanmasıdır; mevcut kendinden imzalı sertifika için beklenen güven sınırlamasıdır.

Paketleme davranışı için: [PyInstaller'ın tek dosya çalışma açıklaması](https://pyinstaller.org/en/stable/operating-mode.html#how-the-one-file-program-works).

## Kullanım

1. EXE dosyasını açın. Python kurulumu gerekmez.
2. Kendi hesabınızın kullanıcı token’ini ve kaynak/hedef sunucu ID’lerini girin.
3. Önizlemeyi inceleyip kopyalamayı başlatın. Hedef sunucunun sahibi veya Yönetici yetkili olmalısınız; kaynak yapıya erişiminiz bulunmalıdır.
4. İlerlemeyi işlem günlüğünden takip edin. Silinemeyen roller/kanallar isim ve ID ile kırmızı gösterilir; işlem devam eder.

**Kopyalama hedefte mevcut rol ve kanalları silmeye çalışır. Kanal silinmesi içindeki mesajları da kaybettirebilir. İkinci onay penceresi yoktur; hedef ID’sini önizlemede kontrol edin.** Yerel yedek yalnızca yapı kaydıdır; otomatik geri yükleme ve mesaj kurtarma sağlamaz. İptal/hata tamamlanmış işlemleri geri almaz.

Yapı yedekleri `%LOCALAPPDATA%\SunucuKopyalayici\backups` altında tutulur; arayüzdeki düğmeyle açılabilir.

Kullanıcı hesabı otomasyonu Discord kurallarına aykırı olabilir ve hesabınızın kısıtlanmasına yol açabilir. Yalnızca kendi hesabınızla ve yönetmeye yetkili olduğunuz sunucularda kullanın. Token’inizi kimseyle paylaşmayın.

## Kaynaktan çalıştırma ve EXE oluşturma

Windows 10/11 x64, Python 3.14 ve PowerShell ile:

```powershell
.\build.ps1
```

Bu komut sanal ortamı/bağımlılıkları hazırlar, testleri çalıştırır, `dist/Sunucu-Kopyalama_v1.0.1.exe` üretir ve paketlenmiş arayüzün öz denetimini çalıştırır. Derleme bağımlılıklarının kurulumu paket kayıt sistemlerine bağlanır; bu, son kullanıcının EXE çalışma akışından ayrıdır.

Kaynaktan açmak için:

```powershell
.\.venv\Scripts\python.exe app.py
```

## Doğrulama

v1.0.1 için 43 otomatik test (31 çekirdek/aktarım, 12 arayüz) ve üretilen EXE’nin arayüz öz denetimi geçti. Ağ testleri taklit yanıtlarla çalışır. Önceki çalışan çekirdeğin gerçek kopyalama işlemini kullanıcı doğruladı; bu sürümdeki görsel değişiklikler sonrasında tüm canlı Discord senaryoları ayrıca denenmedi.

## Lisans

[MIT](LICENSE). CustomTkinter arayüzü/simgesi ve diğer bileşenlerin lisansları [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) dosyasındadır. Discord ile bağlantılı veya Discord tarafından onaylanmış bir ürün değildir.

Derleme notu: gereksiz toplu paket dosyaları kaldırılmıştır; gerekli font/tema ve çalışma zamanı standart PyInstaller hook’larıyla eklenir. UPX kullanılmaz. Dosya ve ürün sürümü 1.0.1.0, dil Türkçe (Türkiye) olarak doldurulur. Antivirüs motorlarının tümü için temiz sonuç garantisi verilmez.
