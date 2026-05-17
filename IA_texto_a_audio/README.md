# IA_edge_tts — TTS sincronizado con SRT usando Microsoft Edge TTS

Script para convertir texto a voz usando Microsoft Edge TTS. Tiene dos modos de uso:

**Modo texto simple** — convierte texto directo o un archivo `.txt` a audio WAV, sin necesidad de SRT ni video.

**Modo SRT (sincronizado con video)** — genera audio perfectamente sincronizado con un archivo SRT. El audio final tiene **exactamente la misma duración** que el audio original de referencia. Soporta traducción offline.

- **Solo TTS** — lee el SRT en el idioma que ya tiene, con la voz que elijas
- **Traducción + TTS** — traduce el SRT a otro idioma offline y genera el audio sincronizado

---

## Requisitos del sistema

- **OS:** Arch Linux
- **Python 3.12**
- **ffmpeg y ffprobe** — para manipular, concatenar y ajustar velocidad del audio
- **Conexión a internet** — requerida para Edge TTS (servicio de Microsoft). La traducción es offline.

---

## 1. Instalar Python 3.12

```bash
yay -S python312
curl https://bootstrap.pypa.io/get-pip.py | python3.12
```

---

## 2. Instalar ffmpeg

```bash
sudo pacman -S ffmpeg
```

ffmpeg y ffprobe son requeridos para: convertir el audio generado por Edge TTS, ajustar velocidad de cada segmento, insertar silencios, concatenar y recortar el audio final.

---

## 3. Instalar dependencias de Python

```bash
python3.12 -m pip install edge-tts argostranslate
```

- **edge-tts** — interfaz con el servicio TTS de Microsoft Edge (requiere internet solo en el momento de generar)
- **argostranslate** — motor de traducción completamente offline

> La primera vez que se use `--translate` con un par de idiomas nuevo, argostranslate descarga el paquete de traducción (~100 MB). Solo ocurre una vez; queda en caché.

---

## 4. Verificar instalación

```bash
python3.12 IA_edge_tts.py --help
```

Para listar todas las voces disponibles directamente desde Edge TTS:

```bash
edge-tts --list-voices

# Filtrar por idioma
edge-tts --list-voices | grep es-MX
edge-tts --list-voices | grep en-US
edge-tts --list-voices | grep fr-FR
```

---

## Cómo funciona la sincronización

El script construye el audio como una **línea de tiempo fija** de 0 hasta la duración total del audio original. Cada segmento SRT ocupa exactamente su rango `[start, end]`. Los huecos entre segmentos son silencio puro. No hay acumulación de errores porque siempre se referencia el tiempo absoluto del SRT, no un cursor relativo.

Por cada segmento:
1. Genera el audio TTS con Edge TTS
2. Calcula la velocidad necesaria para que quepa exactamente en su slot de tiempo
3. Ajusta la velocidad con ffmpeg (dentro de los límites `--min-speed` / `--max-speed`)
4. Recorta o rellena con silencio para forzar la duración exacta del slot
5. Inserta silencio antes del segmento si hay hueco desde el cursor actual

Al final concatena todo y hace un recorte/relleno final para garantizar la duración exacta.

---

## Argumentos

### Modo texto simple (sin SRT)

| Argumento | Descripción |
|-----------|-------------|
| `--text TEXTO` | Texto directo a convertir en audio. Ejemplo: `--text "Hola mundo"` |
| `--txt-file ARCHIVO.txt` | Archivo `.txt` a convertir en audio. Ejemplo: `--txt-file mi_texto.txt` |

### Modo SRT

| Argumento | Descripción |
|-----------|-------------|
| `--sub ARCHIVO.srt` | Archivo SRT de entrada (requerido en modo SRT) |

### Opcionales (ambos modos)

| Argumento | Default | Descripción |
|-----------|---------|-------------|
| `--voice NOMBRE_VOZ` | `es-MX-DaliaNeural` | Voz Edge TTS a usar. Si no se especifica, se elige automáticamente según el idioma destino de `--translate` |
| `-o`, `--output SALIDA.wav` | auto | Nombre del WAV de salida. Default: `<fuente>_tts.wav` |
| `--translate FROM TO` | None | (Solo modo SRT) Traducir el SRT antes del TTS. Ejemplo: `--translate es en` |
| `--audio ARCHIVO.wav` | None | (Solo modo SRT) Audio original para medir duración total exacta. Si no se indica, se usa el tiempo del último segmento del SRT |
| `--max-speed N` | `1.9` | (Solo modo SRT) Velocidad máxima para comprimir segmentos largos. Rango recomendado: 1.5 – 2.0 |
| `--min-speed N` | `0.8` | (Solo modo SRT) Velocidad mínima para expandir segmentos cortos. Rango recomendado: 0.7 – 1.0 |
| `--keep-segments` | False | (Solo modo SRT) Guardar los WAV individuales de cada segmento en `<nombre_salida>_segments/` |

---

## Archivos de salida

Si no se especifica `-o`, el nombre se genera automáticamente:

**Modo texto simple:**
- Con `--txt-file mi_texto.txt` → `mi_texto_tts.wav`
- Con `--text "..."` → `texto_tts.wav`

**Modo SRT:**
- Con `--translate es en` → `<nombre_srt>_en.wav` y `<nombre_srt>_en.srt`
- Sin `--translate` → `<nombre_srt>_tts.wav`

El SRT original **nunca se modifica**. Si se usa `--translate`, se guarda un SRT nuevo con el sufijo del idioma destino junto al original.

---

## Idiomas soportados para traducción (`--translate`)

El script usa `argostranslate` para traducir offline. Las voces por defecto asignadas a cada idioma son:

| Código | Idioma | Voz por defecto |
|--------|--------|-----------------|
| `es` | Español (México) | `es-MX-DaliaNeural` |
| `en` | Inglés (USA) | `en-US-AriaNeural` |
| `fr` | Francés | `fr-FR-DeniseNeural` |
| `de` | Alemán | `de-DE-KatjaNeural` |
| `pt` | Portugués (Brasil) | `pt-BR-FranciscaNeural` |
| `it` | Italiano | `it-IT-ElsaNeural` |
| `ja` | Japonés | `ja-JP-NanamiNeural` |
| `zh` | Chino (Mandarín) | `zh-CN-XiaoxiaoNeural` |
| `ru` | Ruso | `ru-RU-SvetlanaNeural` |
| `ko` | Coreano | `ko-KR-SunHiNeural` |
| `nl` | Holandés | `nl-NL-ColetteNeural` |
| `pl` | Polaco | `pl-PL-ZofiaNeural` |
| `ar` | Árabe | `ar-SA-ZariyahNeural` |

La voz por defecto se usa cuando no se especifica `--voice`. Siempre se puede sobreescribir con `--voice <nombre>`.

---

## Lista completa de voces Edge TTS

Edge TTS ofrece más de **400 voces neuronales** en más de 100 idiomas y variantes regionales. A continuación se listan todas las voces agrupadas por idioma. Para escuchar muestras: https://geeksta.net/tools/tts-samples/

### Africaans (Sudáfrica)
| Voz | Género |
|-----|--------|
| `af-ZA-AdriNeural` | Femenina |
| `af-ZA-WillemNeural` | Masculina |

### Amhárico (Etiopía)
| Voz | Género |
|-----|--------|
| `am-ET-AmehaNeural` | Masculina |
| `am-ET-MekdesNeural` | Femenina |

### Árabe
| Voz | Región | Género |
|-----|--------|--------|
| `ar-AE-FatimaNeural` | Emiratos Árabes | Femenina |
| `ar-AE-HamdanNeural` | Emiratos Árabes | Masculina |
| `ar-BH-AliNeural` | Baréin | Masculina |
| `ar-BH-LailaNeural` | Baréin | Femenina |
| `ar-DZ-AminaNeural` | Argelia | Femenina |
| `ar-DZ-IsmaelNeural` | Argelia | Masculina |
| `ar-EG-SalmaNeural` | Egipto | Femenina |
| `ar-EG-ShakirNeural` | Egipto | Masculina |
| `ar-IQ-BasselNeural` | Iraq | Masculina |
| `ar-IQ-RanaNeural` | Iraq | Femenina |
| `ar-JO-SanaNeural` | Jordania | Femenina |
| `ar-JO-TaimNeural` | Jordania | Masculina |
| `ar-KW-FahedNeural` | Kuwait | Masculina |
| `ar-KW-NouraNeural` | Kuwait | Femenina |
| `ar-LB-LaylaNeural` | Líbano | Femenina |
| `ar-LB-RamiNeural` | Líbano | Masculina |
| `ar-LY-ImanNeural` | Libia | Femenina |
| `ar-LY-OmarNeural` | Libia | Masculina |
| `ar-MA-JamalNeural` | Marruecos | Masculina |
| `ar-MA-MounaNeural` | Marruecos | Femenina |
| `ar-OM-AbdullahNeural` | Omán | Masculina |
| `ar-OM-AyshaNeural` | Omán | Femenina |
| `ar-QA-AmalNeural` | Catar | Femenina |
| `ar-QA-MoazNeural` | Catar | Masculina |
| `ar-SA-HamedNeural` | Arabia Saudí | Masculina |
| `ar-SA-ZariyahNeural` | Arabia Saudí | Femenina |
| `ar-SY-AmanyNeural` | Siria | Femenina |
| `ar-SY-LaithNeural` | Siria | Masculina |
| `ar-TN-HediNeural` | Túnez | Masculina |
| `ar-TN-ReemNeural` | Túnez | Femenina |
| `ar-YE-MaryamNeural` | Yemen | Femenina |
| `ar-YE-SalehNeural` | Yemen | Masculina |

### Azerbaiyano
| Voz | Género |
|-----|--------|
| `az-AZ-BabekNeural` | Masculina |
| `az-AZ-BanuNeural` | Femenina |

### Búlgaro
| Voz | Género |
|-----|--------|
| `bg-BG-BorislavNeural` | Masculina |
| `bg-BG-KalinaNeural` | Femenina |

### Bengalí
| Voz | Región | Género |
|-----|--------|--------|
| `bn-BD-NabanitaNeural` | Bangladesh | Femenina |
| `bn-BD-PradeepNeural` | Bangladesh | Masculina |
| `bn-IN-BashkarNeural` | India | Masculina |
| `bn-IN-TanishaaNeural` | India | Femenina |

### Bosnio
| Voz | Género |
|-----|--------|
| `bs-BA-GoranNeural` | Masculina |
| `bs-BA-VesnaNeural` | Femenina |

### Catalán
| Voz | Género |
|-----|--------|
| `ca-ES-EnricNeural` | Masculina |
| `ca-ES-JoanaNeural` | Femenina |

### Checo
| Voz | Género |
|-----|--------|
| `cs-CZ-AntoninNeural` | Masculina |
| `cs-CZ-VlastaNeural` | Femenina |

### Galés
| Voz | Género |
|-----|--------|
| `cy-GB-AledNeural` | Masculina |
| `cy-GB-NiaNeural` | Femenina |

### Danés
| Voz | Género |
|-----|--------|
| `da-DK-ChristelNeural` | Femenina |
| `da-DK-JeppeNeural` | Masculina |

### Alemán
| Voz | Región | Género |
|-----|--------|--------|
| `de-AT-IngridNeural` | Austria | Femenina |
| `de-AT-JonasNeural` | Austria | Masculina |
| `de-CH-JanNeural` | Suiza | Masculina |
| `de-CH-LeniNeural` | Suiza | Femenina |
| `de-DE-AmalaNeural` | Alemania | Femenina |
| `de-DE-BerndNeural` | Alemania | Masculina |
| `de-DE-ChristophNeural` | Alemania | Masculina |
| `de-DE-ConradNeural` | Alemania | Masculina |
| `de-DE-ElkeNeural` | Alemania | Femenina |
| `de-DE-FlorianMultilingualNeural` | Alemania | Masculina |
| `de-DE-GiselaNeural` | Alemania | Femenina (infantil) |
| `de-DE-KasperNeural` | Alemania | Masculina |
| `de-DE-KatjaNeural` | Alemania | Femenina ⭐ |
| `de-DE-KillianNeural` | Alemania | Masculina |
| `de-DE-KlarissaNeural` | Alemania | Femenina |
| `de-DE-KlausNeural` | Alemania | Masculina |
| `de-DE-LouisaNeural` | Alemania | Femenina |
| `de-DE-MajaNeural` | Alemania | Femenina |
| `de-DE-RalfNeural` | Alemania | Masculina |
| `de-DE-SeraphinaMultilingualNeural` | Alemania | Femenina |
| `de-DE-TanjaNeural` | Alemania | Femenina |

### Griego
| Voz | Género |
|-----|--------|
| `el-GR-AthinaNeural` | Femenina |
| `el-GR-NestorasNeural` | Masculina |

### Inglés
| Voz | Región | Género |
|-----|--------|--------|
| `en-AU-AnnetteNeural` | Australia | Femenina |
| `en-AU-CarlyNeural` | Australia | Femenina |
| `en-AU-DarrenNeural` | Australia | Masculina |
| `en-AU-DuncanNeural` | Australia | Masculina |
| `en-AU-ElsieNeural` | Australia | Femenina |
| `en-AU-FreyaNeural` | Australia | Femenina |
| `en-AU-JoanneNeural` | Australia | Femenina |
| `en-AU-KenNeural` | Australia | Masculina |
| `en-AU-KimNeural` | Australia | Femenina |
| `en-AU-NatashaNeural` | Australia | Femenina |
| `en-AU-NeilNeural` | Australia | Masculina |
| `en-AU-TimNeural` | Australia | Masculina |
| `en-AU-TinaNeural` | Australia | Femenina |
| `en-AU-WilliamNeural` | Australia | Masculina |
| `en-CA-ClaraNeural` | Canadá | Femenina |
| `en-CA-LiamNeural` | Canadá | Masculina |
| `en-GB-AbbiNeural` | Reino Unido | Femenina |
| `en-GB-AlfieNeural` | Reino Unido | Masculina |
| `en-GB-BellaNeural` | Reino Unido | Femenina |
| `en-GB-ElliotNeural` | Reino Unido | Masculina |
| `en-GB-EthanNeural` | Reino Unido | Masculina |
| `en-GB-HollieNeural` | Reino Unido | Femenina |
| `en-GB-LibbyNeural` | Reino Unido | Femenina |
| `en-GB-MaisieNeural` | Reino Unido | Femenina (infantil) |
| `en-GB-NoahNeural` | Reino Unido | Masculina |
| `en-GB-OliverNeural` | Reino Unido | Masculina |
| `en-GB-OliviaNeural` | Reino Unido | Femenina |
| `en-GB-RyanNeural` | Reino Unido | Masculina ⭐ |
| `en-GB-SoniaNeural` | Reino Unido | Femenina ⭐ |
| `en-GB-ThomasNeural` | Reino Unido | Masculina |
| `en-HK-SamNeural` | Hong Kong | Masculina |
| `en-HK-YanNeural` | Hong Kong | Femenina |
| `en-IE-ConnorNeural` | Irlanda | Masculina |
| `en-IE-EmilyNeural` | Irlanda | Femenina |
| `en-IN-NeerjaExpressiveNeural` | India | Femenina |
| `en-IN-NeerjaNeural` | India | Femenina |
| `en-IN-PrabhatNeural` | India | Masculina |
| `en-KE-AsiliaNeural` | Kenia | Femenina |
| `en-KE-ChilembaNeural` | Kenia | Masculina |
| `en-NG-AbeoNeural` | Nigeria | Masculina |
| `en-NG-EzinneNeural` | Nigeria | Femenina |
| `en-NZ-MitchellNeural` | Nueva Zelanda | Masculina |
| `en-NZ-MollyNeural` | Nueva Zelanda | Femenina |
| `en-PH-JamesNeural` | Filipinas | Masculina |
| `en-PH-RosaNeural` | Filipinas | Femenina |
| `en-SG-LunaNeural` | Singapur | Femenina |
| `en-SG-WayneNeural` | Singapur | Masculina |
| `en-TZ-ElimuNeural` | Tanzania | Masculina |
| `en-TZ-ImaniNeural` | Tanzania | Femenina |
| `en-US-AIGenerate1Neural` | USA | Masculina |
| `en-US-AIGenerate2Neural` | USA | Femenina |
| `en-US-AmberNeural` | USA | Femenina |
| `en-US-AnaNeural` | USA | Femenina (infantil) |
| `en-US-AriaNeural` | USA | Femenina ⭐ |
| `en-US-AshleyNeural` | USA | Femenina |
| `en-US-BrandonNeural` | USA | Masculina |
| `en-US-ChristopherNeural` | USA | Masculina |
| `en-US-CoraNeural` | USA | Femenina |
| `en-US-DavisNeural` | USA | Masculina |
| `en-US-ElizabethNeural` | USA | Femenina |
| `en-US-EmmaMultilingualNeural` | USA | Femenina |
| `en-US-EmmaNeural` | USA | Femenina |
| `en-US-EricNeural` | USA | Masculina |
| `en-US-GuyNeural` | USA | Masculina ⭐ |
| `en-US-JacobNeural` | USA | Masculina |
| `en-US-JaneNeural` | USA | Femenina |
| `en-US-JasonNeural` | USA | Masculina |
| `en-US-JennyMultilingualNeural` | USA | Femenina |
| `en-US-JennyNeural` | USA | Femenina ⭐ |
| `en-US-MichelleNeural` | USA | Femenina |
| `en-US-MonicaNeural` | USA | Femenina |
| `en-US-NancyNeural` | USA | Femenina |
| `en-US-RogerNeural` | USA | Masculina |
| `en-US-RyanMultilingualNeural` | USA | Masculina |
| `en-US-SaraNeural` | USA | Femenina |
| `en-US-SteffanNeural` | USA | Masculina |
| `en-US-TonyNeural` | USA | Masculina |
| `en-ZA-LeahNeural` | Sudáfrica | Femenina |
| `en-ZA-LukeNeural` | Sudáfrica | Masculina |

### Español
| Voz | Región | Género |
|-----|--------|--------|
| `es-AR-ElenaNeural` | Argentina | Femenina |
| `es-AR-TomasNeural` | Argentina | Masculina |
| `es-BO-MarceloNeural` | Bolivia | Masculina |
| `es-BO-SofiaNeural` | Bolivia | Femenina |
| `es-CL-CatalinaNeural` | Chile | Femenina |
| `es-CL-LorenzoNeural` | Chile | Masculina |
| `es-CO-GonzaloNeural` | Colombia | Masculina |
| `es-CO-SalomeNeural` | Colombia | Femenina |
| `es-CR-JuanNeural` | Costa Rica | Masculina |
| `es-CR-MariaNeural` | Costa Rica | Femenina |
| `es-CU-BelkysNeural` | Cuba | Femenina |
| `es-CU-ManuelNeural` | Cuba | Masculina |
| `es-DO-EmilioNeural` | Rep. Dominicana | Masculina |
| `es-DO-RamonaNeural` | Rep. Dominicana | Femenina |
| `es-EC-AndreaNeural` | Ecuador | Femenina |
| `es-EC-LuisNeural` | Ecuador | Masculina |
| `es-ES-AbrilNeural` | España | Femenina |
| `es-ES-AlvaroNeural` | España | Masculina ⭐ |
| `es-ES-ArnauNeural` | España | Masculina |
| `es-ES-DarioNeural` | España | Masculina |
| `es-ES-EliasNeural` | España | Masculina |
| `es-ES-ElviraNeural` | España | Femenina ⭐ |
| `es-ES-EstrellaNeural` | España | Femenina |
| `es-ES-IreneNeural` | España | Femenina |
| `es-ES-LaiaNeural` | España | Femenina |
| `es-ES-LiaNeural` | España | Femenina |
| `es-ES-NilNeural` | España | Masculina |
| `es-ES-SaulNeural` | España | Masculina |
| `es-ES-TeoNeural` | España | Masculina |
| `es-ES-TrianaNeural` | España | Femenina |
| `es-ES-VeraNeural` | España | Femenina |
| `es-ES-XimenaNeural` | España | Femenina |
| `es-GQ-JavierNeural` | Guinea Ecuatorial | Masculina |
| `es-GQ-TeresaNeural` | Guinea Ecuatorial | Femenina |
| `es-GT-AndresNeural` | Guatemala | Masculina |
| `es-GT-MartaNeural` | Guatemala | Femenina |
| `es-HN-CarlosNeural` | Honduras | Masculina |
| `es-HN-KarlaNeural` | Honduras | Femenina |
| `es-MX-BeatrizNeural` | México | Femenina |
| `es-MX-CandelaNeural` | México | Femenina |
| `es-MX-CarlotaNeural` | México | Femenina |
| `es-MX-CecilioNeural` | México | Masculina |
| `es-MX-DaliaNeural` | México | Femenina ⭐ |
| `es-MX-GerardoNeural` | México | Masculina |
| `es-MX-JorgeNeural` | México | Masculina ⭐ |
| `es-MX-LarissaNeural` | México | Femenina |
| `es-MX-LibertoNeural` | México | Masculina |
| `es-MX-LucianoNeural` | México | Masculina |
| `es-MX-MarinaNeural` | México | Femenina |
| `es-MX-NuriaNeural` | México | Femenina |
| `es-MX-PelayoNeural` | México | Masculina |
| `es-MX-RenataNeural` | México | Femenina |
| `es-MX-YagoNeural` | México | Masculina |
| `es-NI-FedericoNeural` | Nicaragua | Masculina |
| `es-NI-YolandaNeural` | Nicaragua | Femenina |
| `es-PA-MargaritaNeural` | Panamá | Femenina |
| `es-PA-RobertoNeural` | Panamá | Masculina |
| `es-PE-AlexNeural` | Perú | Masculina |
| `es-PE-CamilaNeural` | Perú | Femenina |
| `es-PR-KarinaNeural` | Puerto Rico | Femenina |
| `es-PR-VictorNeural` | Puerto Rico | Masculina |
| `es-PY-MarioNeural` | Paraguay | Masculina |
| `es-PY-TaniaNeural` | Paraguay | Femenina |
| `es-SV-LorenaNeural` | El Salvador | Femenina |
| `es-SV-RodrigoNeural` | El Salvador | Masculina |
| `es-US-AlonsoNeural` | USA (español) | Masculina |
| `es-US-PalomaNeural` | USA (español) | Femenina |
| `es-UY-MateoNeural` | Uruguay | Masculina |
| `es-UY-ValentinaNeural` | Uruguay | Femenina |
| `es-VE-PaolaNeural` | Venezuela | Femenina |
| `es-VE-SebastianNeural` | Venezuela | Masculina |

### Estonio
| Voz | Género |
|-----|--------|
| `et-EE-AnuNeural` | Femenina |
| `et-EE-KertNeural` | Masculina |

### Persa (Farsi)
| Voz | Género |
|-----|--------|
| `fa-IR-DilaraNeural` | Femenina |
| `fa-IR-FaridNeural` | Masculina |

### Finlandés
| Voz | Género |
|-----|--------|
| `fi-FI-HarriNeural` | Masculina |
| `fi-FI-NooraNeural` | Femenina |
| `fi-FI-SelmaNeural` | Femenina |

### Filipino
| Voz | Género |
|-----|--------|
| `fil-PH-AngeloNeural` | Masculina |
| `fil-PH-BlessicaNeural` | Femenina |

### Francés
| Voz | Región | Género |
|-----|--------|--------|
| `fr-BE-CharlineNeural` | Bélgica | Femenina |
| `fr-BE-GerardNeural` | Bélgica | Masculina |
| `fr-CA-AntoineNeural` | Canadá | Masculina |
| `fr-CA-JeanNeural` | Canadá | Masculina |
| `fr-CA-SylvieNeural` | Canadá | Femenina |
| `fr-CA-ThierryNeural` | Canadá | Masculina |
| `fr-CH-ArianeNeural` | Suiza | Femenina |
| `fr-CH-FabriceNeural` | Suiza | Masculina |
| `fr-FR-AlainNeural` | Francia | Masculina |
| `fr-FR-BrigitteNeural` | Francia | Femenina |
| `fr-FR-CelesteNeural` | Francia | Femenina |
| `fr-FR-ClaudeNeural` | Francia | Masculina |
| `fr-FR-CoralieNeural` | Francia | Femenina |
| `fr-FR-DeniseNeural` | Francia | Femenina ⭐ |
| `fr-FR-EloiseNeural` | Francia | Femenina (infantil) |
| `fr-FR-HenriNeural` | Francia | Masculina ⭐ |
| `fr-FR-JacquelineNeural` | Francia | Femenina |
| `fr-FR-JeromeNeural` | Francia | Masculina |
| `fr-FR-JosephineNeural` | Francia | Femenina |
| `fr-FR-MauriceNeural` | Francia | Masculina |
| `fr-FR-RemyMultilingualNeural` | Francia | Masculina |
| `fr-FR-VivienneMultilingualNeural` | Francia | Femenina |
| `fr-FR-YvesNeural` | Francia | Masculina |
| `fr-FR-YvetteNeural` | Francia | Femenina |

### Irlandés (Gaélico)
| Voz | Género |
|-----|--------|
| `ga-IE-ColmNeural` | Masculina |
| `ga-IE-OrlaNeural` | Femenina |

### Gallego
| Voz | Género |
|-----|--------|
| `gl-ES-RoiNeural` | Masculina |
| `gl-ES-SabelaNeural` | Femenina |

### Gujarati
| Voz | Género |
|-----|--------|
| `gu-IN-DhwaniNeural` | Femenina |
| `gu-IN-NiranjanNeural` | Masculina |

### Hebreo
| Voz | Género |
|-----|--------|
| `he-IL-AvriNeural` | Masculina |
| `he-IL-HilaNeural` | Femenina |

### Hindi
| Voz | Género |
|-----|--------|
| `hi-IN-MadhurNeural` | Masculina |
| `hi-IN-SwaraNeural` | Femenina ⭐ |

### Croata
| Voz | Género |
|-----|--------|
| `hr-HR-GabrijelaNeural` | Femenina |
| `hr-HR-SreckoNeural` | Masculina |

### Húngaro
| Voz | Género |
|-----|--------|
| `hu-HU-NoemiNeural` | Femenina |
| `hu-HU-TamasNeural` | Masculina |

### Indonesio
| Voz | Género |
|-----|--------|
| `id-ID-ArdiNeural` | Masculina |
| `id-ID-GadisNeural` | Femenina |

### Islandés
| Voz | Género |
|-----|--------|
| `is-IS-GudrunNeural` | Femenina |
| `is-IS-GunnarNeural` | Masculina |

### Italiano
| Voz | Región | Género |
|-----|--------|--------|
| `it-IT-BenignoNeural` | Italia | Masculina |
| `it-IT-CalimeroNeural` | Italia | Masculina |
| `it-IT-CataldoNeural` | Italia | Masculina |
| `it-IT-DiegoNeural` | Italia | Masculina |
| `it-IT-ElsaNeural` | Italia | Femenina ⭐ |
| `it-IT-FabiolaNeural` | Italia | Femenina |
| `it-IT-FiammaNeural` | Italia | Femenina |
| `it-IT-GianniNeural` | Italia | Masculina |
| `it-IT-GiuseppeMultilingualNeural` | Italia | Masculina |
| `it-IT-ImeldaNeural` | Italia | Femenina |
| `it-IT-IrmaNeural` | Italia | Femenina |
| `it-IT-IsabellaNeural` | Italia | Femenina |
| `it-IT-LisandroNeural` | Italia | Masculina |
| `it-IT-PalmiraNeural` | Italia | Femenina |
| `it-IT-PierinaNeural` | Italia | Femenina |
| `it-IT-RinaldoNeural` | Italia | Masculina |

### Japonés
| Voz | Género |
|-----|--------|
| `ja-JP-AoiNeural` | Femenina |
| `ja-JP-DaichiNeural` | Masculina |
| `ja-JP-KeitaNeural` | Masculina |
| `ja-JP-MayuNeural` | Femenina |
| `ja-JP-NanamiNeural` | Femenina ⭐ |
| `ja-JP-NaokiNeural` | Masculina |
| `ja-JP-ShioriNeural` | Femenina |

### Javanés
| Voz | Género |
|-----|--------|
| `jv-ID-DimasNeural` | Masculina |
| `jv-ID-SitiNeural` | Femenina |

### Georgiano
| Voz | Género |
|-----|--------|
| `ka-GE-EkaNeural` | Femenina |
| `ka-GE-GiorgiNeural` | Masculina |

### Kazajo
| Voz | Género |
|-----|--------|
| `kk-KZ-AigulNeural` | Femenina |
| `kk-KZ-DauletNeural` | Masculina |

### Jemer (Camboyano)
| Voz | Género |
|-----|--------|
| `km-KH-PisethNeural` | Masculina |
| `km-KH-SreymomNeural` | Femenina |

### Kannada
| Voz | Género |
|-----|--------|
| `kn-IN-GaganNeural` | Masculina |
| `kn-IN-SapnaNeural` | Femenina |

### Coreano
| Voz | Género |
|-----|--------|
| `ko-KR-BongJinNeural` | Masculina |
| `ko-KR-GookMinNeural` | Masculina |
| `ko-KR-HyunsuMultilingualNeural` | Masculina |
| `ko-KR-InJoonNeural` | Masculina |
| `ko-KR-JiMinNeural` | Femenina |
| `ko-KR-SeoHyeonNeural` | Femenina |
| `ko-KR-SoonBokNeural` | Femenina |
| `ko-KR-SunHiNeural` | Femenina ⭐ |
| `ko-KR-YuJinNeural` | Femenina |

### Lao
| Voz | Género |
|-----|--------|
| `lo-LA-ChanthavongNeural` | Masculina |
| `lo-LA-KeomanyNeural` | Femenina |

### Lituano
| Voz | Género |
|-----|--------|
| `lt-LT-LeonasNeural` | Masculina |
| `lt-LT-OnaNeural` | Femenina |

### Letón
| Voz | Género |
|-----|--------|
| `lv-LV-EveritaNeural` | Femenina |
| `lv-LV-NilsNeural` | Masculina |

### Macedonio
| Voz | Género |
|-----|--------|
| `mk-MK-AleksandarNeural` | Masculina |
| `mk-MK-MarijaNeural` | Femenina |

### Malayalam
| Voz | Género |
|-----|--------|
| `ml-IN-MidhunNeural` | Masculina |
| `ml-IN-SobhanaNeural` | Femenina |

### Mongol
| Voz | Género |
|-----|--------|
| `mn-MN-BataaNeural` | Masculina |
| `mn-MN-YesuiNeural` | Femenina |

### Maratí
| Voz | Género |
|-----|--------|
| `mr-IN-AarohiNeural` | Femenina |
| `mr-IN-ManoharNeural` | Masculina |

### Malayo
| Voz | Región | Género |
|-----|--------|--------|
| `ms-MY-OsmanNeural` | Malasia | Masculina |
| `ms-MY-YasminNeural` | Malasia | Femenina |

### Maltés
| Voz | Género |
|-----|--------|
| `mt-MT-GraceNeural` | Femenina |
| `mt-MT-JosephNeural` | Masculina |

### Birmano
| Voz | Género |
|-----|--------|
| `my-MM-NilarNeural` | Femenina |
| `my-MM-ThihaNeural` | Masculina |

### Noruego
| Voz | Género |
|-----|--------|
| `nb-NO-FinnNeural` | Masculina |
| `nb-NO-IselinNeural` | Femenina |
| `nb-NO-PernilleNeural` | Femenina |

### Nepalés
| Voz | Género |
|-----|--------|
| `ne-NP-HemkalaNeural` | Femenina |
| `ne-NP-SagarNeural` | Masculina |

### Holandés
| Voz | Región | Género |
|-----|--------|--------|
| `nl-BE-ArnaudNeural` | Bélgica | Masculina |
| `nl-BE-DenaNeural` | Bélgica | Femenina |
| `nl-NL-ColetteNeural` | Países Bajos | Femenina ⭐ |
| `nl-NL-FennaNeural` | Países Bajos | Femenina |
| `nl-NL-MaartenNeural` | Países Bajos | Masculina |

### Polaco
| Voz | Género |
|-----|--------|
| `pl-PL-AgnieszkaNeural` | Femenina |
| `pl-PL-MarekNeural` | Masculina |
| `pl-PL-ZofiaNeural` | Femenina ⭐ |

### Pastún
| Voz | Género |
|-----|--------|
| `ps-AF-GulNawazNeural` | Masculina |
| `ps-AF-LatifaNeural` | Femenina |

### Portugués
| Voz | Región | Género |
|-----|--------|--------|
| `pt-BR-AntonioNeural` | Brasil | Masculina |
| `pt-BR-BrendaNeural` | Brasil | Femenina |
| `pt-BR-DonatoNeural` | Brasil | Masculina |
| `pt-BR-ElzaNeural` | Brasil | Femenina |
| `pt-BR-FabioNeural` | Brasil | Masculina |
| `pt-BR-FranciscaNeural` | Brasil | Femenina ⭐ |
| `pt-BR-GiovannaNeural` | Brasil | Femenina |
| `pt-BR-HumbertoNeural` | Brasil | Masculina |
| `pt-BR-JulioNeural` | Brasil | Masculina |
| `pt-BR-LeilaNeural` | Brasil | Femenina |
| `pt-BR-LeticiaNeural` | Brasil | Femenina |
| `pt-BR-ManuelaNeural` | Brasil | Femenina |
| `pt-BR-NicolauNeural` | Brasil | Masculina |
| `pt-BR-ThalitaNeural` | Brasil | Femenina |
| `pt-BR-ValerioNeural` | Brasil | Masculina |
| `pt-BR-YaraNeural` | Brasil | Femenina |
| `pt-PT-DuarteNeural` | Portugal | Masculina |
| `pt-PT-FernandaNeural` | Portugal | Femenina |
| `pt-PT-RaquelNeural` | Portugal | Femenina ⭐ |

### Rumano
| Voz | Género |
|-----|--------|
| `ro-RO-AlinaNeural` | Femenina |
| `ro-RO-EmilNeural` | Masculina |

### Ruso
| Voz | Género |
|-----|--------|
| `ru-RU-DariyaNeural` | Femenina |
| `ru-RU-DmitryNeural` | Masculina |
| `ru-RU-SvetlanaNeural` | Femenina ⭐ |

### Sinhala
| Voz | Género |
|-----|--------|
| `si-LK-SameeraNeural` | Masculina |
| `si-LK-ThiliniNeural` | Femenina |

### Eslovaco
| Voz | Género |
|-----|--------|
| `sk-SK-LukasNeural` | Masculina |
| `sk-SK-ViktoriaNeural` | Femenina |

### Esloveno
| Voz | Género |
|-----|--------|
| `sl-SI-PetraNeural` | Femenina |
| `sl-SI-RokNeural` | Masculina |

### Somalí
| Voz | Género |
|-----|--------|
| `so-SO-MuuseNeural` | Masculina |
| `so-SO-UbaxNeural` | Femenina |

### Albanés
| Voz | Género |
|-----|--------|
| `sq-AL-AnilaNeural` | Femenina |
| `sq-AL-IlirNeural` | Masculina |

### Serbio
| Voz | Género |
|-----|--------|
| `sr-RS-NicholasNeural` | Masculina |
| `sr-RS-SophieNeural` | Femenina |

### Sundanés
| Voz | Género |
|-----|--------|
| `su-ID-JajangNeural` | Masculina |
| `su-ID-TutiNeural` | Femenina |

### Sueco
| Voz | Género |
|-----|--------|
| `sv-SE-HilleviNeural` | Femenina |
| `sv-SE-MattiasNeural` | Masculina |
| `sv-SE-SofieNeural` | Femenina |

### Suajili
| Voz | Región | Género |
|-----|--------|--------|
| `sw-KE-RafikiNeural` | Kenia | Masculina |
| `sw-KE-ZuriNeural` | Kenia | Femenina |
| `sw-TZ-DaudiNeural` | Tanzania | Masculina |
| `sw-TZ-RehemaNeural` | Tanzania | Femenina |

### Tamil
| Voz | Región | Género |
|-----|--------|--------|
| `ta-IN-PallaviNeural` | India | Femenina |
| `ta-IN-ValluvarNeural` | India | Masculina |
| `ta-LK-KumarNeural` | Sri Lanka | Masculina |
| `ta-LK-SaranyaNeural` | Sri Lanka | Femenina |
| `ta-MY-KaniNeural` | Malasia | Femenina |
| `ta-MY-SuryaNeural` | Malasia | Masculina |
| `ta-SG-AnbuNeural` | Singapur | Masculina |
| `ta-SG-VenbaNeural` | Singapur | Femenina |

### Telugu
| Voz | Género |
|-----|--------|
| `te-IN-MohanNeural` | Masculina |
| `te-IN-ShrutiNeural` | Femenina |

### Tailandés
| Voz | Género |
|-----|--------|
| `th-TH-AcharaNeural` | Femenina |
| `th-TH-NiwatNeural` | Masculina |
| `th-TH-PremwadeeNeural` | Femenina |

### Turco
| Voz | Género |
|-----|--------|
| `tr-TR-AhmetNeural` | Masculina |
| `tr-TR-EmelNeural` | Femenina ⭐ |

### Ucraniano
| Voz | Género |
|-----|--------|
| `uk-UA-OstapNeural` | Masculina |
| `uk-UA-PolinaNeural` | Femenina |

### Urdu
| Voz | Región | Género |
|-----|--------|--------|
| `ur-IN-GulNeural` | India | Femenina |
| `ur-IN-SalmanNeural` | India | Masculina |
| `ur-PK-AsadNeural` | Pakistán | Masculina |
| `ur-PK-UzmaNeural` | Pakistán | Femenina |

### Uzbeko
| Voz | Género |
|-----|--------|
| `uz-UZ-MadinaNeural` | Femenina |
| `uz-UZ-SardorNeural` | Masculina |

### Vietnamita
| Voz | Género |
|-----|--------|
| `vi-VN-HoaiMyNeural` | Femenina |
| `vi-VN-NamMinhNeural` | Masculina |

### Chino
| Voz | Región | Género |
|-----|--------|--------|
| `wuu-CN-XiaotongNeural` | Shanghainés | Femenina |
| `wuu-CN-YunzheNeural` | Shanghainés | Masculina |
| `yue-CN-XiaoMinNeural` | Cantonés (China) | Femenina |
| `yue-CN-YunSongNeural` | Cantonés (China) | Masculina |
| `zh-CN-XiaochenNeural` | Mandarín (China) | Femenina |
| `zh-CN-XiaochenMultilingualNeural` | Mandarín (China) | Femenina |
| `zh-CN-XiaohanNeural` | Mandarín (China) | Femenina |
| `zh-CN-XiaomengNeural` | Mandarín (China) | Femenina |
| `zh-CN-XiaomoNeural` | Mandarín (China) | Femenina |
| `zh-CN-XiaoqiuNeural` | Mandarín (China) | Femenina |
| `zh-CN-XiaoruiNeural` | Mandarín (China) | Femenina |
| `zh-CN-XiaoshuangNeural` | Mandarín (China) | Femenina (infantil) |
| `zh-CN-XiaoxiaoNeural` | Mandarín (China) | Femenina ⭐ |
| `zh-CN-XiaoxuanNeural` | Mandarín (China) | Femenina |
| `zh-CN-XiaoyanNeural` | Mandarín (China) | Femenina |
| `zh-CN-XiaoyiNeural` | Mandarín (China) | Femenina |
| `zh-CN-XiaoyouNeural` | Mandarín (China) | Femenina (infantil) |
| `zh-CN-XiaozhenNeural` | Mandarín (China) | Femenina |
| `zh-CN-YunfengNeural` | Mandarín (China) | Masculina |
| `zh-CN-YunhaoNeural` | Mandarín (China) | Masculina |
| `zh-CN-YunjianNeural` | Mandarín (China) | Masculina |
| `zh-CN-YunxiNeural` | Mandarín (China) | Masculina ⭐ |
| `zh-CN-YunxiaNeural` | Mandarín (China) | Masculina |
| `zh-CN-YunyangNeural` | Mandarín (China) | Masculina ⭐ |
| `zh-CN-YunyeNeural` | Mandarín (China) | Masculina |
| `zh-CN-YunzeNeural` | Mandarín (China) | Masculina |
| `zh-CN-YunzeMultilingualNeural` | Mandarín (China) | Masculina |
| `zh-HK-HiuGaaiNeural` | Cantonés (Hong Kong) | Femenina ⭐ |
| `zh-HK-HiuMaanNeural` | Cantonés (Hong Kong) | Femenina |
| `zh-HK-WanLungNeural` | Cantonés (Hong Kong) | Masculina |
| `zh-TW-HsiaoChenNeural` | Mandarín (Taiwán) | Femenina ⭐ |
| `zh-TW-HsiaoYuNeural` | Mandarín (Taiwán) | Femenina |
| `zh-TW-YunJheNeural` | Mandarín (Taiwán) | Masculina |

### Zulú
| Voz | Género |
|-----|--------|
| `zu-ZA-ThandoNeural` | Femenina |
| `zu-ZA-ThembaNeural` | Masculina |

> ⭐ = recomendadas. Para escuchar muestras de todas las voces: https://geeksta.net/tools/tts-samples/
>
> La lista puede cambiar con actualizaciones del servicio. Para ver las voces actuales disponibles en tiempo real: `edge-tts --list-voices`

---

## Ejemplos

### Texto simple — directo desde la terminal

```bash
# Voz por defecto (es-MX-DaliaNeural), salida automática: texto_tts.wav
python3.12 IA_edge_tts.py --text "Hola, esto es una prueba de voz."

# Con voz y salida específica
python3.12 IA_edge_tts.py --text "Buenos días a todos." \
    --voice es-MX-JorgeNeural -o saludo.wav

# En inglés
python3.12 IA_edge_tts.py --text "Hello, this is a voice test." \
    --voice en-US-AriaNeural -o hello.wav
```

### Texto simple — desde un archivo .txt

```bash
# Voz por defecto, salida automática: mi_texto_tts.wav
python3.12 IA_edge_tts.py --txt-file mi_texto.txt

# Con voz y salida específica
python3.12 IA_edge_tts.py --txt-file mi_texto.txt \
    --voice es-MX-JorgeNeural -o narracion.wav

# Texto largo en inglés
python3.12 IA_edge_tts.py --txt-file article.txt \
    --voice en-US-GuyNeural -o article_audio.wav
```

### Modo SRT — solo TTS sin traducir

```bash
# Voz inglés por defecto
python3.12 IA_edge_tts.py --sub ./subs/video.srt --audio video.wav -o video_tts.wav

# Con voz española específica
python3.12 IA_edge_tts.py --sub ./subs/video.srt --audio video.wav \
    -o video_tts.wav --voice es-MX-JorgeNeural
```

### Modo SRT — traducir y generar TTS

```bash
# Español → inglés (voz automática: en-US-AriaNeural)
python3.12 IA_edge_tts.py --translate es en \
    --sub ./subs/video.srt --audio video.wav -o video_en.wav

# Español → francés con voz masculina personalizada
python3.12 IA_edge_tts.py --translate es fr \
    --sub ./subs/video.srt --audio video.wav -o video_fr.wav \
    --voice fr-FR-HenriNeural

# Español → alemán
python3.12 IA_edge_tts.py --translate es de \
    --sub ./subs/video.srt --audio video.wav -o video_de.wav

# Español → japonés
python3.12 IA_edge_tts.py --translate es ja \
    --sub ./subs/video.srt --audio video.wav -o video_ja.wav
```

### Modo SRT — sin audio original (duración tomada del SRT)

```bash
python3.12 IA_edge_tts.py --translate es en \
    --sub ./subs/video.srt -o video_en.wav
```

### Modo SRT — guardar segmentos individuales

```bash
python3.12 IA_edge_tts.py --translate es en \
    --sub ./subs/video.srt --audio video.wav -o video_en.wav \
    --keep-segments
# → genera video_en_segments/seg_0000.wav, seg_0001.wav, ...
```

### Modo SRT — ajustar límites de velocidad

```bash
# Más permisivo (comprime hasta 2.5x si el segmento es muy largo)
python3.12 IA_edge_tts.py --translate es en \
    --sub ./subs/video.srt --audio video.wav -o video_en.wav \
    --max-speed 2.5 --min-speed 0.7
```

---

## Cómo funciona la traducción

`argostranslate` agrupa los segmentos del SRT en **frases completas** antes de traducir (por puntuación final, silencios >0.4s o texto >120 caracteres). Esto produce traducciones más coherentes y naturales que traducir segmento a segmento. El SRT resultante tiene menos líneas pero frases completas.

El SRT original **nunca se modifica**. Se guarda un archivo nuevo con el sufijo del idioma destino (ej: `video_en.srt`).

---

## Problemas conocidos

**Error de conexión en TTS** — Edge TTS requiere internet. Verificar la conexión. Si el servicio de Microsoft falla temporalmente, los segmentos afectados se rellenan con silencio y se reportan en el resumen como errores.

**Segmentos muy rápidos o con voz cortada** — el texto es más largo que el slot de tiempo disponible y se comprimió al máximo (`--max-speed`). Subir `--max-speed` a 2.2 o 2.5, o usar un SRT con segmentos más espaciados.

**Segmentos lentos o con pausas notables** — el texto es muy corto para el slot. Bajar `--min-speed` a 0.7 o usar `--max-speed` más bajo para evitar expansión excesiva.

**Primera traducción lenta** — descarga el paquete de idioma de argostranslate (~100 MB). Solo ocurre la primera vez por par de idiomas.

**Voz no encontrada** — verificar el nombre exacto de la voz con `edge-tts --list-voices`. Los nombres son sensibles a mayúsculas.
