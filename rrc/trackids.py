"""RaceRoom internal ID tables (layout IDs, car IDs).

RaceRoom single-player result files name the track only by an
internal numeric layout ID and vehicles sometimes only by a car ID.
These tables map those IDs to readable names. Source: community
r3e-data.json (kwstudios r3e-spectator-overlay), plus user-defined
mappings stored in track_names.json in the app data directory.
"""

# layout ID -> (track name, layout name)
LAYOUTS = {
    263: ("RaceRoom Raceway", "Grand Prix"),
    264: ("RaceRoom Raceway", "Classic"),
    265: ("RaceRoom Raceway", "Classic Sprint"),
    266: ("RaceRoom Raceway", "Bridge"),
    267: ("RaceRoom Raceway", "National"),
    1671: ("Monza Circuit", "Grand Prix"),
    1672: ("Monza Circuit", "Junior"),
    1674: ("Mid Ohio", "Full"),
    1675: ("Mid Ohio", "Short"),
    1676: ("Mid Ohio", "Chicane"),
    1678: ("Circuit Zandvoort 2019", "Grand Prix"),
    1679: ("Circuit Zandvoort 2019", "Club"),
    1680: ("Circuit Zandvoort 2019", "National"),
    1682: ("Lakeview Hillclimb", "Full Run"),
    1684: ("Circuit Zolder", "Grand Prix"),
    1691: ("Nürburgring", "Grand Prix"),
    1693: ("Hockenheimring", "Grand Prix"),
    1709: ("RaceRoom Hillclimb", "Full Run"),
    1763: ("Hockenheimring", "National"),
    1764: ("Hockenheimring", "Short"),
    1778: ("Portimao Circuit", "Grand Prix"),
    1783: ("Portimao Circuit", "Moto"),
    1784: ("Portimao Circuit", "Chicane"),
    1785: ("Portimao Circuit", "Short"),
    1841: ("Suzuka Circuit", "Grand Prix"),
    1846: ("Bathurst Circuit", "Mount Panorama"),
    1850: ("Imola", "Grand Prix"),
    1852: ("Indianapolis 2012", "Grand Prix"),
    1854: ("Sonoma Raceway", "WTCC"),
    1856: ("WeatherTech Raceway Laguna Seca", "Grand Prix"),
    1866: ("Hungaroring", "Grand Prix"),
    2010: ("Nürburgring", "Grand Prix Fast Chicane"),
    2011: ("Nürburgring", "Sprint Fast Chicane"),
    2012: ("Suzuka Circuit", "East Course"),
    2013: ("Suzuka Circuit", "West Course"),
    2014: ("Indianapolis 2012", "Moto"),
    2016: ("Sonoma Raceway", "Sprint"),
    2024: ("Estoril Circuit", "Grand Prix"),
    2026: ("Salzburgring", "Grand Prix"),
    2027: ("Shanghai Circuit", "Grand Prix"),
    2064: ("Slovakia Ring", "Grand Prix"),
    2123: ("Macau", "Grand Prix"),
    2181: ("Lakeview Hillclimb", "Reverse"),
    2214: ("RaceRoom Hillclimb", "Reverse"),
    2384: ("Motorsport Arena Oschersleben", "A Course"),
    2468: ("DEKRA Lausitzring", "DTM Short Course"),
    2473: ("Moscow Raceway", "Sprint"),
    2518: ("Norisring", "Grand Prix"),
    2520: ("Brands Hatch Indy", "Indy"),
    2556: ("Red Bull Ring Spielberg", "Grand Prix Circuit"),
    2813: ("Nordschleife", "Nordschleife"),
    2867: ("Paul Ricard", "Solution 3C"),
    3291: ("DEKRA Lausitzring", "Short Course"),
    3377: ("Nürburgring", "Sprint"),
    3383: ("Moscow Raceway", "Full"),
    3464: ("Zhuhai Circuit", "Grand Prix"),
    3538: ("Sachsenring", "Grand Prix"),
    3683: ("Moscow Raceway", "FIM"),
    3870: ("Spa-Francorchamps 2015", "Grand Prix"),
    3912: ("Sonoma Raceway", "Long"),
    3913: ("Sonoma Raceway", "IRL"),
    4039: ("Silverstone Circuit", "Grand Prix"),
    4041: ("Shanghai Circuit", "Intermediate (WTCC)"),
    4042: ("Shanghai Circuit", "West Long"),
    4246: ("Paul Ricard", "Solution 1A-V2"),
    4247: ("Paul Ricard", "Solution 1C-V2"),
    4248: ("Paul Ricard", "Solution 2A short"),
    4253: ("Chang International Circuit", "Full Circuit"),
    4542: ("Spa-Francorchamps 2015", "Classic"),
    4543: ("Spa-Francorchamps 2015", "Combined"),
    4944: ("Chang International Circuit", "D Circuit"),
    4975: ("Nordschleife", "NLS"),
    5093: ("Nordschleife", "Tourist"),
    5095: ("Nordschleife", "24 Hours"),
    5276: ("Road America", "Grand Prix"),
    5298: ("Brno", "Grand Prix"),
    5301: ("Anderstorp Raceway", "Grand Prix"),
    5794: ("Red Bull Ring Spielberg", "Südschleife National Circuit"),
    5816: ("Silverstone Circuit", "International"),
    5817: ("Silverstone Circuit", "National"),
    5862: ("Silverstone Circuit", "Historic Grand Prix"),
    5925: ("Gelleråsen Arena", "Grand Prix Circuit"),
    6010: ("Mantorp Park", "Long Circuit"),
    6055: ("Stowe Circuit", "Long"),
    6056: ("Stowe Circuit", "Short"),
    6137: ("Knutstorp Ring", "GP"),
    6138: ("Gelleråsen Arena", "Short Circuit"),
    6140: ("Falkenberg Motorbana", "Grand Prix"),
    6164: ("Anderstorp Raceway", "South"),
    6166: ("DEKRA Lausitzring", "Grand Prix Course"),
    6167: ("Mantorp Park", "Short Circuit"),
    6341: ("Sepang", "Grand Prix"),
    6578: ("Sepang", "North"),
    6579: ("Sepang", "South"),
    6587: ("Dubai Autodrome", "Grand Prix Circuit"),
    6658: ("Twin Ring Motegi", "Road Course"),
    7026: ("Twin Ring Motegi", "West Course"),
    7027: ("Twin Ring Motegi", "East Course"),
    7112: ("Autodrom Most", "Grand Prix"),
    7273: ("Ningbo International Speedpark", "Full circuit"),
    7753: ("Motorsport Arena Oschersleben", "B Course"),
    7754: ("Motorsport Arena Oschersleben", "Motorcycle A Course"),
    7755: ("Motorsport Arena Oschersleben", "Motorcycle B Course"),
    7819: ("Bilster Berg", "Gesamtstrecke"),
    7976: ("Dubai Autodrome", "Club Circuit"),
    7977: ("Dubai Autodrome", "National Circuit"),
    7978: ("Dubai Autodrome", "International Circuit"),
    8069: ("Bilster Berg", "Gesamtstrecke Schikane"),
    8070: ("Bilster Berg", "Ostschleife"),
    8071: ("Bilster Berg", "Ostschleife Schikane"),
    8075: ("Zhejiang Circuit", "Grand Prix"),
    8095: ("Bilster Berg", "Westschleife"),
    8309: ("Ningbo International Speedpark", "Full circuit no chicane"),
    8310: ("Ningbo International Speedpark", "Intermediate circuit"),
    8311: ("Ningbo International Speedpark", "Intermediate circuit no chicane"),
    8314: ("Ningbo International Speedpark", "Short circuit"),
    8327: ("Zhejiang Circuit", "East circuit"),
    8367: ("Daytona International Speedway", "Road Course"),
    8648: ("Daytona International Speedway", "Speedway (Not Supported)"),
    8655: ("Daytona International Speedway", "Road Course Motorcycle (2006)"),
    8704: ("Motorland Aragón", "Grand Prix"),
    9040: ("Motorland Aragón", "Motorcycle Grand Prix"),
    9041: ("Motorland Aragón", "National"),
    9042: ("Motorland Aragón", "Motorcycle National"),
    9043: ("Motorland Aragón", "Fast Circuit"),
    9055: ("DEKRA Lausitzring", "DTM Grand Prix Course"),
    9177: ("Watkins Glen International", "Short with Inner loop"),
    9321: ("Genting Highlands Highway", "Stage"),
    9324: ("Watkins Glen International", "Grand Prix with Inner Loop"),
    9343: ("Watkins Glen International", "Short Circuit"),
    9344: ("Watkins Glen International", "Grand Prix"),
    9360: ("Genting Highlands Highway", "Circuit"),
    9465: ("Vålerbanen", "Full Circuit"),
    9473: ("Brands Hatch Grand Prix", "Grand Prix"),
    9483: ("Motorland Aragón", "WTCR"),
    9659: ("Nogaro Circuit Paul Armagnac", "Grand Prix Circuit"),
    9796: ("Brno", "Grand Prix (Short Pit Entry)"),
    9839: ("Twin Forest", "Duel"),
    9847: ("Nürburgring", "Müllenbachschleife"),
    9943: ("Indianapolis Motor Speedway", "Road Course"),
    9957: ("Indianapolis Motor Speedway", "Historic"),
    9958: ("Indianapolis Motor Speedway", "Oval"),
    9985: ("TT Circuit Assen", "Grand Prix"),
    10258: ("Nogaro Circuit Paul Armagnac", "Club Circuit"),
    10274: ("Hockenheimring DMEC", "DMEC"),
    10328: ("DEKRA Lausitzring", "GP Course Oval T1"),
    10351: ("TT Circuit Assen", "North Course"),
    10355: ("TT Circuit Assen", "Motorcycle Course"),
    10392: ("Nogaro Circuit Paul Armagnac", "Caupenne Circuit"),
    10394: ("Donington Park", "Grand Prix"),
    10414: ("RaceRoom Raceway", "Drift Area"),
    10463: ("Interlagos", "Grand Prix"),
    10725: ("Donington Park", "National"),
    10782: ("Circuit Zandvoort", "Grand Prix"),
    10904: ("Circuit de Charade", "Grand Prix"),
    11090: ("Circuit Zandvoort", "Short"),
    11296: ("Red Bull Ring Spielberg", "Moto"),
    11859: ("Genting Highlands Highway", "Dual Stage"),
    11861: ("Genting Highlands Highway", "Short Stage"),
    11905: ("Circuit de Pau-Ville", "Grand Prix"),
    11908: ("Circuit de Charade", "Classic Racing School"),
    11909: ("Paul Ricard", "Solution 1A"),
    12112: ("Hockenheimring Classic", "Grand Prix"),
    12236: ("Hockenheimring Classic", "Short"),
    12268: ("Silverstone Circuit Classic", "Grand Prix"),
    12318: ("Estoril Circuit", "Tanque"),
    12389: ("Silverstone Circuit Classic", "National"),
    12390: ("Silverstone Circuit Classic", "International"),
    12395: ("Fliegerhorst Diepholz", "Full Circuit"),
    12420: ("AVUS", "1998"),
    12500: ("AVUS", "1994"),
    12506: ("Motorsport Arena Oschersleben 2024", "Grand Prix"),
    12571: ("Motorsport Arena Oschersleben 2024", "Alternate"),
    12572: ("Motorsport Arena Oschersleben 2024", "Short"),
    12573: ("Nogaro Circuit Paul Armagnac", "Moto Circuit"),
    12938: ("Alemannenring", "Full Circuit"),
    13187: ("Vallelunga", "International"),
    13256: ("Circuit de Spa-Francorchamps", "Grand Prix"),
    13338: ("Vallelunga", "Short"),
    13339: ("Vallelunga", "Chicane"),
    13340: ("Vallelunga", "Classic"),
    13352: ("Adria International Raceway 2003", "Full Circuit"),
    13368: ("Circuit de Spa-Francorchamps", "Classic"),
    13369: ("Circuit de Spa-Francorchamps", "Combined"),
    13425: ("Adria International Raceway 2021", "Full Circuit"),
    13467: ("Circuit de Spa-Francorchamps", "Moto"),
}

# car ID -> car name
CARS = {
    252: "Aquila CR1 Sports GT",
    258: "BMW 134 Judd V8",
    1686: "Saleen S7R",
    1694: "Canhard R51",
    1695: "BMW Alpina B6 GT3",
    1700: "BMW 320 Turbo",
    1733: "BMW M3 E92 GT",
    1738: "BMW Z4 GT3",
    1741: "Canhard R52",
    1744: "Carlsson C25 GT",
    1747: "Chevrolet Corvette C6.R ZR1",
    1750: "Cougar C14-1",
    1753: "Cougar C14-2",
    1756: "DMD P20",
    1759: "DMD P21",
    1779: "Ford GT GT1",
    1782: "Ford Mustang GT3",
    1788: "Gumpert Apollo Sport",
    1794: "Koenigsegg CCGT",
    1797: "McLaren-Mercedes SLR 722 GT",
    1800: "Mistral M530",
    1803: "Mistral M531",
    1807: "Nissan GT-R GT1",
    1811: "Nissan GT-R GT3",
    1815: "Nissan Silvia Turbo",
    1818: "Nissan Skyline 2000RS",
    1821: "P4-5 Competizione GT3",
    1824: "Pagani Zonda R",
    1827: "Radical SR9 AER",
    1831: "Radical SR9 Judd",
    1834: "RUF CTR3",
    1837: "RUF RT12R",
    1862: "BMW 635 CSI",
    1909: "McLaren MP4-12C GT3",
    2037: "Audi R8 LMS Ultra",
    2044: "Zakspeed Capri",
    2116: "BMW M3 E30 Gr.A",
    2275: "Volvo 240 Turbo",
    2333: "Chevrolet Daytona Prototype",
    2338: "Chevrolet Camaro GT3",
    2339: "BMW M1 Procar",
    2405: "Audi 90 Quattro",
    2409: "Ford GT GT3",
    2410: "Cadillac CTS-V.R",
    2413: "DTM Mercedes AMG C-Coupé",
    2417: "BMW M3 DTM ",
    2420: "Audi RS 5 DTM",
    2533: "Mercedes-Benz SLS AMG GT3",
    2611: "Chevrolet Corvette Z06.R GT3",
    2705: "BMW E90 320 TC",
    2728: "Honda Civic WTCC",
    2804: "SEAT León WTCC",
    2842: "Lada Granta WTCC",
    2846: "Chevrolet Cruze WTCC",
    2849: "Carlsson SLK 340 JUDD",
    2859: "Fabcar 935",
    2868: "Nissan 300ZX Z32",
    2923: "Audi R8 LMS Ultra",
    2924: "BMW Z4 GT3",
    2925: "Chevrolet Camaro GT3",
    2926: "Nissan GT-R GT3",
    2927: "Mercedes-Benz SLS AMG GT3",
    3380: "Audi RS 5 DTM 2014",
    3384: "Mercedes-Benz SLS AMG GT3",
    3408: "BMW M4 DTM",
    3479: "DTM Mercedes AMG C Coupe 14",
    3500: "Audi R8 LMS Ultra",
    3508: "Chevrolet Corvette Z06.R GT3",
    3516: "RUF RT12R GTR3",
    3527: "McLaren MP4-12C GT3",
    3530: "BMW Z4 GT3",
    3534: "Chevrolet Camaro GT3",
    3539: "Mercedes 190E Evo II DTM",
    3549: "BMW M3 Sport Evolution",
    3626: "Chevrolet Corvette Z06.R GT3",
    3662: "Audi V8 DTM",
    3754: "Ford GT GT3",
    3842: "Ford Mustang GT DTM",
    3874: "Opel Omega 3000 Evo500",
    3899: "Citroen C Elysee WTCC",
    3964: "Nissan Skyline GTR R32 Group N",
    4046: "Chevrolet RML Cruze TC1",
    4067: "LADA Granta 1.6T",
    4075: "Chevrolet Corvette Greenwood 1977",
    4114: "Nissan R90CK",
    4145: "Chevrolet Dekon Monza",
    4197: "Honda Civic WTCC 2014",
    4261: "Audi RS 5 DTM 2015",
    4264: "Mercedes-AMG C63 DTM",
    4267: "BMW M4 DTM 2015",
    4299: "Audi TT RS VLN",
    4308: "Audi R18",
    4386: "Ford Mustang IMSA GTO",
    4518: "Audi R8 LMS Ultra",
    4544: "BMW Z4 GT3",
    4551: "Mercedes-Benz SLS AMG GT3",
    4554: "Honda Civic WTCC 2015",
    4557: "Nissan GT-R GT3",
    4570: "Chevrolet Corvette Z06.R GT3 GTM15",
    4579: "Chevrolet RML Cruze TC1 2015",
    4582: "Chevrolet Camaro GT3",
    4585: "Citroen C Elysee WTCC 2015",
    4598: "Formula RaceRoom 2",
    4675: "Porsche 911 GT3 Cup (991.2) Endurance",
    4681: "Audi TT cup 2015",
    4720: "Lada Vesta WTCC 2015",
    4810: "NSU TTS",
    4865: "Formula RaceRoom Junior",
    5051: "Tatuus F4",
    5152: "Bentley Continental GT3",
    5170: "Bentley Continental GT3",
    5214: "P4-5 Competizione GT2",
    5259: "Mercedes-AMG C 63 DTM",
    5342: "KTM X-Bow RR",
    5348: "Formula RaceRoom US",
    5396: "Formula RaceRoom 3",
    5399: "BMW M4 DTM 2016",
    5402: "Mercedes-AMG C 63 DTM 2016",
    5411: "Audi RS 5 DTM 2016",
    5588: "Audi TT cup 2016",
    5767: "KTM X-Bow GT4",
    5786: "McLaren 650S GT3",
    5818: "BMW M6 GT3",
    5821: "Formula Raceroom X-17",
    6002: "Volvo S60 Polestar TC1",
    6011: "Chevrolet RML Cruze TC1 2016",
    6017: "Citroen C Elysee WTCC 2016",
    6024: "Honda Civic WTCC 2016",
    6031: "Lada Vesta WTCC 2016",
    6057: "Audi R8 LMS",
    6168: "Mercedes AMG GT3",
    6174: "Callaway Corvette C7 GT3-R",
    6177: "Chevrolet RML Cruze eSports",
    6187: "Citroen C Elysee eSports",
    6195: "Honda Civic eSports",
    6203: "Lada Vesta eSports",
    6208: "Volvo S60 Polestar eSports",
    6262: "BMW M235i Racing",
    6310: "Chevrolet RML Cruze TC1 2017",
    6314: "Citroen C Elysee WTCC 2017",
    6321: "Honda Civic WTCC 2017",
    6329: "Lada Vesta WTCC 2017",
    6334: "Volvo S60 Polestar TC1",
    6349: "Porsche 911 GT3 R",
    6568: "Porsche Cayman GT4 Clubsport",
    6588: "Audi RS 3 LMS",
    6623: "Porsche Cayman GT4 CS MR",
    6791: "AMG-Mercedes CLK DTM 2003",
    6849: "AMG-Mercedes C-Klasse DTM 2005",
    6860: "AMG-Mercedes 190 E 2.5-16 Evolution II 1992",
    6949: "Mercedes-AMG C 63 DTM 2015",
    6978: "AMG-Mercedes C-Klasse DTM 1995",
    7005: "CUPRA TCR",
    7011: "Audi RS 3 LMS",
    7029: "Alfa Romeo Giulietta TCR",
    7036: "Peugeot 308 TCR",
    7040: "Porsche Cayman GT4 Clubsport",
    7076: "AMG-Mercedes C-Klasse DTM",
    7105: "Volkswagen Golf GTI TCR",
    7117: "Hyundai i30 N TCR",
    7125: "Honda Civic TCR",
    7162: "Lotus Evora GT4",
    7169: "AMG-Mercedes CLK DTM",
    7183: "AMG-Mercedes C-Klasse DTM",
    7215: "Formula RR 90 V8",
    7218: "Formula RR 90 V12",
    7220: "Formula RR 90 V10",
    7282: "Porsche 934 Turbo RSR",
    7396: "Porsche 911 Carrera Cup (964)",
    7399: "Porsche 962 C Team Joest",
    7629: "BMW M6 GT3",
    7630: "Audi R8 LMS",
    7640: "Callaway Corvette C7 GT3-R",
    7643: "Mercedes AMG GT3",
    7647: "Porsche 911 GT3 R",
    7805: "BMW M1 Gr. 4",
    7810: "Volkswagen ID. R",
    7845: "Alfa Romeo Giulietta TCR",
    7847: "Audi RS 3 LMS",
    7850: "CUPRA TCR",
    7853: "Honda Civic TCR",
    7856: "Hyundai i30 N TCR",
    7859: "Volkswagen Golf GTI TCR",
    7926: "Lynk & Co 03 TCR",
    7983: "Porsche 911 GT3 Cup",
    8006: "CUPRA TCR",
    8053: "BMW M4 GT4 (F82)",
    8084: "Volkswagen Golf GTI TCR",
    8115: "E36 V8 JUDD",
    8149: "Opel Astra",
    8166: "Porsche 911 GT3 Cup (991.2)",
    8201: "Porsche 718 Cayman GT4 Clubsport",
    8242: "Porsche 911 GT2 RS Clubsport",
    8257: "Porsche 911 GT3 R (2019)",
    8467: "Honda Civic Type R",
    8487: "Porsche 911 RSR 2019",
    8498: "Volkswagen Scirocco Gr2",
    8593: "Bentley Continental GT3 EVO",
    8604: "Audi R8 LMS GT3 EVO",
    8645: "Honda Accord Super Touring",
    8652: "Audi R8 LMS GT2 2019",
    8657: "Audi RS 3 LMS",
    8661: "Hyundai i30 N TCR",
    8677: "Shopping Cart",
    8698: "Lada Vesta",
    8715: "Hyundai i30 N TCR",
    8719: "Lynk & Co 03 TCR",
    8726: "CUPRA Leon Competición",
    8757: "CUPRA Leon e-Racer",
    8776: "Honda Civic TCR",
    8782: "Alfa Romeo Giulietta TCR",
    8785: "Peugeot 308",
    8788: "CUPRA Leon Competición",
    8792: "Porsche 911 GT3 Cup (992) Endurance",
    8900: "Audi R8 LMS GT4 2020",
    8936: "BMW M6 GT3",
    8938: "Porsche 911 GT3 R (2019)",
    8940: "Mercedes AMG GT3",
    8942: "Callaway Corvette C7 GT3-R",
    9031: "Audi R8 LMS",
    9094: "BMW M4 DTM 2020e",
    9102: "Audi RS 5 DTM 2020e",
    9154: "Lynk & Co 03 TCR",
    9206: "Audi RS 5 DTM 2020",
    9220: "BMW M4 DTM 2020",
    9234: "Hyundai i30 N TCR",
    9241: "Lynk & Co 03 TCR",
    9252: "Alfa Romeo Giulietta TCR",
    9256: "Audi RS 3 LMS",
    9266: "Honda Civic TCR",
    9278: "CUPRA Leon Competición",
    9467: "Renault Mégane RS TCR",
    9548: "Audi R8 LMS GT3 EVO",
    9565: "Bentley Continental GT3 EVO",
    9575: "McLaren 720S GT3",
    9581: "Mercedes-AMG GT3 2020",
    9603: "Mercedes-AMG GT3 2020",
    9644: "Mercedes AMG GT4 2020",
    9660: "KTM X-BOW GTX",
    9761: "BMW E30 M3 Drift",
    9986: "RaceRoom Truck",
    10018: "Formula Raceroom X-22",
    10051: "Audi R8 LMS GT3 EVO",
    10076: "BMW M6 GT3",
    10085: "Bentley Continental GT3 EVO",
    10110: "Mercedes-AMG GT3 2020",
    10119: "Porsche 911 GT3 R (2019)",
    10127: "Callaway Corvette C7 GT3-R",
    10263: "Ford Mustang Mach-E 1400",
    10345: "Audi RS 3 LMS 2021",
    10368: "Lynk & Co 03 TCR",
    10371: "CUPRA Leon Competición",
    10387: "Ferrari 488 GT3 EVO 2020 DTM",
    10397: "Hyundai Elantra TCR 2021",
    10401: "Honda Civic TCR",
    10441: "Honda Civic TCR",
    10541: "Audi R8 LMS GT3 EVO DTM",
    10546: "BMW M6 GT3 DTM",
    10552: "McLaren 720S GT3 DTM",
    10556: "Mercedes-AMG GT3 2020 DTM",
    10564: "Porsche 911 GT3 R (2019) DTM",
    10578: "Audi RS 3 LMS",
    10599: "BMW M2 CS Racing 2021",
    10604: "BMW G82 M4 Drift",
    10674: "Lada Vesta TCR",
    10721: "S.C. Cupra TCR",
    10744: "McLaren 570s GT4",
    10787: "Audi R8 LMS GT3 EVO",
    10790: "Bentley Continental GT3 EVO",
    10795: "BMW M6 GT3",
    10804: "McLaren 720S GT3",
    10806: "Mercedes-AMG GT3 2020",
    10808: "Porsche 911 GT3 R (2019)",
    10890: "Ferrari 488 GT3 EVO 2020",
    10896: "Crosslé 90F",
    10914: "Mazda MX-5 CUP 2019 ND2",
    10918: "Audi R8 LMS GT3 EVO eDTM",
    10920: "BMW M6 GT3 eDTM",
    10924: "Ferrari 488 GT3 EVO 2020 eDTM",
    10945: "Mercedes-AMG GT3 2020 eDTM",
    10950: "Porsche 911 GT3 R (2019) eDTM",
    11025: "Callaway Corvette C7 GT3-R",
    11051: "Praga R1",
    11285: "Crosslé 9S",
    11318: "Hyundai Elantra TCR 2022",
    11320: "Honda Civic TCR",
    11323: "CUPRA Leon Competición",
    11325: "Audi RS 3 LMS 2021",
    11328: "Lynk & Co 03 TCR",
    11342: "Mazda RT24 P DPi",
    11474: "Formula Raceroom X-22 Esports",
    11536: "BMW M4 GT3",
    11561: "Porsche 944 Turbo Cup",
    11567: "Audi R8 LMS GT3 EVO",
    11586: "BMW M6 GT3",
    11589: "Mercedes-AMG GT3 2020",
    11597: "Porsche 911 GT3 R (2019)",
    11917: "Audi RS 3 LMS 2021",
    11922: "Hyundai Elantra TCR 2022",
    11991: "KTM X-BOW GT2",
    12012: "Porsche 911 GT3 Cup (992) Endurance",
    12090: "Porsche 911 GT3 R (992)",
    12163: "Porsche 911 GT3 Cup (992)",
    12197: "Porsche 911 GT3 R (992) DTM",
    12237: "BMW M4 GT3 DTM",
    12240: "Mercedes-AMG GT3 2020 DTM",
    12319: "Audi R8 LMS GT3 EVO II",
    12352: "Audi R8 LMS GT3 EVO II DTM",
    12405: "Ferrari 296 GT3",
    12421: "Ferrari 296 GT3 DTM",
    12430: "BMW M8 GTE",
    12509: "BMW M4 GT4 (G82)",
    12537: "S.C. Audi R8 LMS",
    12556: "BMW 320i E36 Super Touring",
    12561: "Audi A4 Super Touring 1995",
    12652: "Volvo 850 Super Touring",
    12771: "Lamborghini Huracán GT3 EVO II",
    12788: "Audi R8 LMS GT3 EVO II DTM",
    12790: "BMW M4 GT3 DTM",
    12792: "Ferrari 296 GT3 DTM",
    12795: "Lamborghini Huracán GT3 EVO II DTM",
    12800: "Mercedes-AMG GT3 2020 DTM",
    12807: "Porsche 911 GT3 R (992) DTM",
    12815: "McLaren 720S GT3 EVO DTM",
    12829: "Volvo S40 Super Touring",
    12839: "Opel Calibra V6 DTM",
    12850: "Alfa Romeo 155 TI DTM 1995",
    12942: "Porsche 911 GT3 Cup (992)",
    13039: "S.C. Cupra Formentor",
    13049: "Alfa Romeo 156 Super Touring",
    13065: "Opel Vectra Super Touring",
    13126: "BMW M Hybrid V8",
    13137: "Lamborghini SC63",
    13141: "Ferrari 296 GT3 DTM",
    13150: "Porsche 911 GT3 R (992) DTM",
    13160: "Lamborghini Huracán GT3 EVO II DTM",
    13164: "Mercedes-AMG GT3 2020 DTM",
    13169: "Porsche 963",
    13172: "BMW M4 GT3 EVO DTM",
    13174: "McLaren 720S GT3 EVO DTM",
    13183: "Renault Laguna Super Touring",
    13190: "Audi R8 LMS GT3 EVO II DTM",
    13265: "AMG-Mercedes CLK-DTM 2002",
    13312: "Abt-Audi TT-R",
    13323: "Opel Astra V8 Coupé",
    13355: "LRT NXT1",
    13394: "Alpine A110 Cup",
    13398: "Alpine A110 GT4+",
    13524: "Porsche 911 GT3 R (992.2)",
    13572: "Porsche 911 GT3 R (992.2) DTM",
    13591: "Ford Mustang GT3 EVO DTM",
    13594: "Lamborghini Temerario GT3 DTM",
    13597: "Mercedes-AMG GT3 2020 DTM",
    13603: "Aston Martin Vantage AMR GT3 EVO DTM",
    13617: "BMW M4 GT3 EVO DTM",
    13620: "McLaren 720S GT3 EVO DTM",
}


def resolve_layout(layout_id):
    """Return (track, layout) names for a numeric layout ID or None."""
    try:
        return LAYOUTS.get(int(layout_id))
    except (TypeError, ValueError):
        return None


def resolve_car(car_id):
    """Return the car name for a numeric car ID or None."""
    try:
        return CARS.get(int(car_id))
    except (TypeError, ValueError):
        return None


def is_id(value):
    """True if the value is a pure numeric ID string."""
    try:
        s = str(value).strip()
        return s.isdigit() and int(s) > 0
    except Exception:
        return False


def user_names_path(app_dir):
    """Path of the user-defined ID mapping file inside the app data folder."""
    import os
    return os.path.join(app_dir, "track_names.json")


def load_user_names(path):
    """Load user-defined mappings: {"layouts": {"<id>": [track, layout]},
    "cars": {"<id>": name}}. Missing file returns empty structure."""
    import json
    data = {"layouts": {}, "cars": {}}
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if isinstance(raw, dict):
            for k, v in (raw.get("layouts") or {}).items():
                if isinstance(v, (list, tuple)) and len(v) == 2:
                    data["layouts"][str(int(k))] = [str(v[0]), str(v[1])]
            for k, v in (raw.get("cars") or {}).items():
                data["cars"][str(int(k))] = str(v)
    except (OSError, ValueError, TypeError):
        pass
    return data


def save_user_names(path, data):
    """Atomically save user-defined mappings."""
    import json
    import os
    clean = {
        "layouts": {str(k): [str(v[0]), str(v[1])]
                    for k, v in (data.get("layouts") or {}).items()},
        "cars": {str(k): str(v) for k, v in (data.get("cars") or {}).items()},
    }
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(clean, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def resolve_layout_with(layout_id, user=None, official=None):
    """Resolve a layout ID. Priority: user mappings, then the official
    game data (r3e-data.json of the RaceRoom installation), then the
    built-in tables. Returns (track, layout) or None."""
    if user:
        v = (user.get("layouts") or {}).get(str(layout_id))
        if v:
            return (v[0], v[1])
    if official:
        v = (official.get("layouts") or {}).get(_as_int(layout_id))
        if v:
            return (v[0], v[1])
    return resolve_layout(layout_id)


def resolve_car_with(car_id, user=None, official=None):
    """Resolve a car ID. Priority: user mappings, then the official game
    data, then the built-in tables."""
    if user:
        v = (user.get("cars") or {}).get(str(car_id))
        if v:
            return v
    if official:
        v = (official.get("cars") or {}).get(_as_int(car_id))
        if v:
            return v
    return resolve_car(car_id)


def _as_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def official_data_path(install_dir):
    """Standard path of the official r3e-data.json inside a RaceRoom
    installation folder."""
    import os
    return os.path.join(install_dir, "Game", "GameData", "General",
                        "r3e-data.json")


def find_official_data(install_dir):
    """Locate r3e-data.json below the given RaceRoom folder.
    Returns the full path or None if not present."""
    import os
    if not install_dir:
        return None
    candidates = [
        official_data_path(install_dir),
        os.path.join(install_dir, "GameData", "General", "r3e-data.json"),
        os.path.join(install_dir, "r3e-data.json"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def load_official(install_dir):
    """Load ID tables from the official r3e-data.json shipped with the
    game (kept current by every game update). Returns
    {"layouts": {id: (track, layout)}, "cars": {id: name}} or None if
    the folder is invalid or the file unreadable. Supports both the
    game schema (tracks with nested layouts) and the flat community
    schema (top-level "layouts" with TrackId references)."""
    import json
    path = find_official_data(install_dir)
    if not path:
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    layouts = {}
    cars = {}
    track_names = {}
    for tid, t in (data.get("tracks") or {}).items():
        if not isinstance(t, dict):
            continue
        name = t.get("Name") or t.get("name") or ""
        if name:
            track_names[str(tid)] = str(name)
        for lay in t.get("layouts") or []:
            if isinstance(lay, dict) and lay.get("Id") is not None:
                lid = _as_int(lay.get("Id"))
                if lid is not None:
                    layouts[lid] = (str(name), str(lay.get("Name") or ""))
    # Community (overlay) schema fallback: flat layout table
    for lid, lay in (data.get("layouts") or {}).items():
        if not isinstance(lay, dict):
            continue
        key = _as_int(lid)
        if key is None or key in layouts:
            continue
        tname = track_names.get(str(lay.get("TrackId") or ""), "")
        layouts[key] = (tname, str(lay.get("Name") or ""))
    for cid, c in (data.get("cars") or {}).items():
        if isinstance(c, dict):
            name = c.get("Name") or c.get("name")
            if not name:
                continue
            key = _as_int(cid)
            if key is not None:
                cars[key] = str(name)
        elif isinstance(c, str) and c:
            key = _as_int(cid)
            if key is not None:
                cars[key] = c
    if not layouts and not cars:
        return None
    return {"layouts": layouts, "cars": cars}
