#!/usr/bin/env python3
"""Build the Open Door Index data.js from the passport-index dataset.

Reads the (refreshed) passport-index CSVs in this repo and emits a single
data.js consumed by the Open Door Index page (passport-design-recovery/final).

What it computes, per the page's three maps:

  1. Passport strength (our method) — for each passport, the sum of annual
     tourist arrivals across every destination it can enter without a
     pre-issued visa (visa-free / VOA / eTA / numeric stay). Tourism-weighted,
     not a flat country count.

  2. Hospitality balance — per country, how welcoming it is (`ac` = how many of
     the 199 passports it admits visa-free) versus how much it relies on others'
     openness (its own reach as a share of the world). A net-positive country
     opens its door wider than the world opens to it (green); a net-negative
     country leans on others' hospitality more than it returns it (red).

  3. Net tourism balance — incoming arrivals (`v`, UNWTO) minus outbound
     departures (`out`, UNWTO). Net-positive = host nation (green); net-negative
     = sending nation (red). Restores the travel-flows (incoming vs outgoing)
     data lost in the earlier redesign.

Disputed / unrecognised territories are flagged `disputed: true` so the page can
colour them gray and stay out of politics.

Run from this repo's root:
    python3 build_open_door_data.py
Override the output path with:
    python3 build_open_door_data.py /path/to/data.js
"""
import csv
import json
import os
import sys

# Default output: the Open Door Index page's data.js, sibling repo on disk.
DEFAULT_OUT = os.path.expanduser(
    "~/projects/passport-design-recovery/final/data.js"
)

# --- Incoming international tourist arrivals, millions/yr (UNWTO, latest) ----
TOURISM = {
'France':100,'Spain':94,'United States':72,'Italy':57,'Turkey':56,'Mexico':45,'United Kingdom':38,'Germany':35,'Greece':33,'Austria':32,'Japan':32,'Canada':22,'China':65,'Thailand':35,'Saudi Arabia':30,'Hungary':16,'Portugal':27,'Croatia':21,'Netherlands':20,'Poland':17,'Hong Kong':34,'Macao':28,'United Arab Emirates':22,'Malaysia':25,'Russia':9,'Czech Republic':13,'South Korea':17,'Singapore':16,'Indonesia':14,'Vietnam':17,'Switzerland':12,'Egypt':15,'Morocco':17,'Argentina':8,'Brazil':7,'Australia':9,'India':10,'South Africa':9,'Ireland':11,'Denmark':14,'Sweden':8,'Belgium':10,'Bulgaria':12,'Romania':3,'Ukraine':4,'Israel':3,'Iran':5,'New Zealand':3,'Norway':6,'Finland':3,'Iceland':2.3,'Estonia':3.5,'Lithuania':1.8,'Latvia':1.5,'Slovakia':2,'Slovenia':6,'Cyprus':4,'Malta':3,'Luxembourg':1,'Albania':11,'Serbia':2,'Montenegro':2.6,'Bosnia and Herzegovina':1.6,'North Macedonia':1,'Moldova':0.2,'Belarus':0.4,'Georgia':7,'Armenia':2.3,'Azerbaijan':2.5,'Kazakhstan':8,'Uzbekistan':6,'Kyrgyzstan':6,'Tajikistan':1,'Turkmenistan':0.1,'Mongolia':0.6,'Taiwan':6,'Philippines':5.4,'Laos':3.4,'Cambodia':5.4,'Myanmar':0.6,'Sri Lanka':2,'Maldives':1.9,'Nepal':1,'Bangladesh':0.3,'Pakistan':1,'Bhutan':0.1,'Bahrain':9,'Qatar':4,'Kuwait':8,'Oman':4,'Jordan':6,'Lebanon':1.4,'Tunisia':9,'Algeria':2,'Libya':0.05,'Sudan':0.5,'Ethiopia':0.8,'Kenya':2,'Tanzania':2,'Uganda':1.5,'Rwanda':1.4,'Mauritius':1.3,'Seychelles':0.4,'Madagascar':0.3,'Senegal':1.6,'Ghana':1,'Nigeria':1,'Cape Verde':1,'Botswana':1.8,'Namibia':1.6,'Zambia':1.2,'Zimbabwe':2.5,'Mozambique':0.5,'Cameroon':1,'Ivory Coast':2,'Angola':0.6,'Cuba':2.4,'Dominican Republic':8,'Jamaica':4,'Bahamas':7,'Barbados':0.6,'Costa Rica':2.5,'Panama':2.5,'Colombia':5,'Peru':2.5,'Chile':4.5,'Uruguay':3,'Paraguay':1.2,'Ecuador':1.5,'Bolivia':0.5,'Venezuela':0.5,'Guatemala':2.5,'Honduras':1,'Nicaragua':0.5,'El Salvador':2.5,'Belize':0.5,'Trinidad and Tobago':0.4,'Andorra':9.6,'Monaco':0.4,'San Marino':0.06,'Vatican':5,'Liechtenstein':0.1,'Fiji':0.9,'Vanuatu':0.1,'Samoa':0.2,'Tonga':0.1,'Papua New Guinea':0.2,'Solomon Islands':0.03,'Palau':0.05,'Micronesia':0.02,'Marshall Islands':0.005,'Kiribati':0.005,'Tuvalu':0.001,'Nauru':0.001,'Brunei':0.3,'Timor-Leste':0.08,'Afghanistan':0.05,'Iraq':1,'Syria':0.5,'Yemen':0.05,'Somalia':0.04,'North Korea':0.005,'Eritrea':0.1,'South Sudan':0.04,'Equatorial Guinea':0.1,'Central African Republic':0.1,'Chad':0.1,'Mali':0.2,'Niger':0.1,'Burkina Faso':0.2,'Togo':0.5,'Benin':0.3,'Liberia':0.05,'Sierra Leone':0.07,'Guinea':0.05,'Guinea-Bissau':0.05,'Mauritania':0.1,'Gambia':0.6,'Djibouti':0.07,'Comoros':0.04,'Sao Tome and Principe':0.04,'Gabon':0.4,'Congo':0.3,'DR Congo':0.4,'Burundi':0.05,'Lesotho':1,'Swaziland':1,'Malawi':0.4,'Dominica':0.08,'Grenada':0.2,'Saint Lucia':0.4,'Saint Vincent and the Grenadines':0.08,'Saint Kitts and Nevis':0.1,'Antigua and Barbuda':0.3,'Haiti':0.2,'Suriname':0.1,'Guyana':0.3,'Palestine':0.7,'Kosovo':0.5,
}

# --- Outbound international tourist departures, millions/yr (UNWTO/World Bank,
#     latest available, post-pandemic recovery basis). Restores the travel-flows
#     (incoming vs outgoing) data lost in the redesign. Countries absent here
#     have no reliable departures series and are rendered "limited data" on the
#     net-tourism map. -------------------------------------------------------
OUTBOUND = {
'China':130,'Hong Kong':105,'Germany':95,'United Kingdom':85,'United States':80,'Russia':32,'Italy':35,'France':32,'Canada':36,'Saudi Arabia':28,'Ukraine':28,'Poland':24,'Netherlands':23,'South Korea':28,'Spain':21,'Japan':17,'India':31,'Belgium':12,'Switzerland':16,'Austria':13,'Sweden':16,'Romania':22,'Czech Republic':13,'Kazakhstan':12,'Norway':10,'Denmark':10,'Ireland':9,'Australia':11,'Singapore':10,'Malaysia':12,'Thailand':10,'Taiwan':12,'Turkey':10,'Hungary':24,'Finland':9,'Portugal':4,'Greece':9,'Slovakia':6,'Slovenia':6,'Croatia':4,'Bulgaria':8,'Lithuania':3,'Latvia':2,'Estonia':3,'Israel':9,'Egypt':6,'Iran':9,'Kuwait':8,'Qatar':3,'United Arab Emirates':6,'Bahrain':12,'Oman':3,'Jordan':4,'Lebanon':3,'Argentina':9,'Brazil':9,'Chile':5,'Mexico':22,'Colombia':5,'Peru':3,'Uruguay':2,'South Africa':6,'Morocco':4,'Tunisia':4,'Algeria':5,'Nigeria':2,'Kenya':1,'Philippines':6,'Indonesia':10,'Vietnam':10,'Pakistan':9,'Bangladesh':3,'Sri Lanka':1,'New Zealand':3,'Belarus':12,'Azerbaijan':5,'Georgia':3,'Armenia':2,'Uzbekistan':14,'Kyrgyzstan':4,'Moldova':3,'Serbia':2,'Luxembourg':2,'Cyprus':1,'Iceland':1.5,'Malta':0.6,
}

# --- Population, millions (for the per-capita stat in the country drawer) ----
POP = {
'China':1410.7,'India':1428.6,'United States':334.9,'Indonesia':277.5,'Pakistan':240.5,'Nigeria':223.8,'Brazil':215.3,'Bangladesh':172.9,'Russia':144.4,'Mexico':128.5,'Japan':124.5,'Ethiopia':126.5,'Philippines':117.3,'Egypt':112.7,'DR Congo':102.3,'Vietnam':98.9,'Iran':89.2,'Turkey':85.3,'Germany':84.5,'Thailand':71.7,'United Kingdom':67.9,'France':68.0,'Tanzania':67.4,'South Africa':60.4,'Italy':58.9,'Kenya':55.1,'Myanmar':54.5,'Colombia':52.1,'South Korea':51.7,'Sudan':48.1,'Uganda':47.2,'Spain':48.3,'Argentina':46.0,'Algeria':45.6,'Iraq':45.5,'Afghanistan':41.1,'Poland':36.7,'Canada':40.1,'Morocco':37.5,'Saudi Arabia':36.9,'Ukraine':36.7,'Angola':36.7,'Yemen':33.7,'Uzbekistan':35.6,'Peru':34.4,'Malaysia':33.9,'Mozambique':33.9,'Ghana':33.5,'Nepal':30.9,'Venezuela':28.4,'Madagascar':30.3,'North Korea':26.2,'Australia':26.7,'Cameroon':28.0,'Ivory Coast':28.9,'Niger':27.2,'Sri Lanka':22.0,'Burkina Faso':23.3,'Mali':23.3,'Romania':19.0,'Chile':19.6,'Kazakhstan':19.6,'Malawi':20.4,'Zambia':20.6,'Syria':23.2,'Ecuador':18.0,'Guatemala':18.0,'Senegal':17.7,'Chad':17.7,'Somalia':18.1,'Zimbabwe':16.3,'Cambodia':16.8,'Netherlands':17.8,'Rwanda':13.8,'Guinea':13.5,'Benin':13.0,'Tunisia':12.5,'Bolivia':12.4,'Belgium':11.7,'Burundi':12.9,'Haiti':11.4,'Cuba':11.3,'Czech Republic':10.9,'Greece':10.4,'Sweden':10.5,'Dominican Republic':11.2,'Jordan':11.3,'Portugal':10.4,'Azerbaijan':10.4,'Hungary':9.6,'Tajikistan':10.1,'United Arab Emirates':9.9,'Belarus':9.2,'Israel':9.8,'Switzerland':8.8,'Papua New Guinea':10.3,'Honduras':10.5,'Sierra Leone':8.6,'Togo':8.9,'Bulgaria':6.7,'Laos':7.6,'Paraguay':6.9,'Hong Kong':7.5,'Nicaragua':6.8,'Libya':6.9,'Lebanon':5.4,'El Salvador':6.4,'Singapore':5.9,'Denmark':5.9,'Finland':5.6,'Norway':5.5,'Slovakia':5.4,'Turkmenistan':6.1,'Kyrgyzstan':6.7,'Eritrea':3.7,'Liberia':5.4,'Costa Rica':5.2,'Central African Republic':5.4,'Ireland':5.3,'Palestine':5.3,'Mauritania':4.9,'Oman':4.6,'New Zealand':5.2,'Panama':4.5,'Croatia':3.8,'Kuwait':4.3,'Mongolia':3.4,'Moldova':3.3,'Bosnia and Herzegovina':3.2,'Uruguay':3.4,'Albania':2.7,'Armenia':2.8,'Lithuania':2.7,'Jamaica':2.8,'Qatar':2.7,'Namibia':2.5,'Botswana':2.4,'Gambia':2.7,'Gabon':2.3,'Lesotho':2.3,'Slovenia':2.1,'North Macedonia':2.1,'Latvia':1.8,'Guinea-Bissau':2.1,'Bahrain':1.5,'Trinidad and Tobago':1.4,'Equatorial Guinea':1.6,'Estonia':1.3,'Mauritius':1.3,'Cyprus':1.3,'Eswatini':1.2,'Swaziland':1.2,'Timor-Leste':1.4,'Djibouti':1.1,'Fiji':0.9,'Comoros':0.84,'Bhutan':0.79,'Solomon Islands':0.74,'Suriname':0.62,'Cape Verde':0.6,'Luxembourg':0.65,'Malta':0.55,'Brunei':0.45,'Maldives':0.52,'Belize':0.41,'Iceland':0.39,'Bahamas':0.41,'Vanuatu':0.33,'Barbados':0.28,'Sao Tome and Principe':0.23,'Samoa':0.22,'Saint Lucia':0.18,'Kiribati':0.13,'Micronesia':0.11,'Tonga':0.11,'Grenada':0.13,'Seychelles':0.12,'Antigua and Barbuda':0.094,'Andorra':0.08,'Dominica':0.073,'Saint Kitts and Nevis':0.048,'Marshall Islands':0.042,'Liechtenstein':0.04,'Monaco':0.039,'San Marino':0.034,'Palau':0.018,'Tuvalu':0.011,'Nauru':0.013,'Vatican':0.0008,'South Sudan':11.1,'Saint Vincent and the Grenadines':0.10,'Kosovo':1.7,'Taiwan':23.4,'Macao':0.7,
}

# --- Disputed / partially recognised. Rendered gray on every map so the page
#     stays out of geopolitics. These are NOT scored. ------------------------
DISPUTED = {'Kosovo', 'Palestine', 'Taiwan'}

EU = {'Albania','Andorra','Austria','Belarus','Belgium','Bosnia and Herzegovina','Bulgaria','Croatia','Cyprus','Czech Republic','Denmark','Estonia','Finland','France','Germany','Greece','Hungary','Iceland','Ireland','Italy','Kosovo','Latvia','Liechtenstein','Lithuania','Luxembourg','Malta','Moldova','Monaco','Montenegro','Netherlands','North Macedonia','Norway','Poland','Portugal','Romania','Russia','San Marino','Serbia','Slovakia','Slovenia','Spain','Sweden','Switzerland','Ukraine','United Kingdom','Vatican'}
AS = {'Afghanistan','Armenia','Azerbaijan','Bahrain','Bangladesh','Bhutan','Brunei','Cambodia','China','Georgia','Hong Kong','India','Indonesia','Iran','Iraq','Israel','Japan','Jordan','Kazakhstan','Kuwait','Kyrgyzstan','Laos','Lebanon','Macao','Malaysia','Maldives','Mongolia','Myanmar','Nepal','North Korea','Oman','Pakistan','Palestine','Philippines','Qatar','Saudi Arabia','Singapore','South Korea','Sri Lanka','Syria','Taiwan','Tajikistan','Thailand','Timor-Leste','Turkey','Turkmenistan','United Arab Emirates','Uzbekistan','Vietnam','Yemen'}
AM = {'Antigua and Barbuda','Argentina','Bahamas','Barbados','Belize','Bolivia','Brazil','Canada','Chile','Colombia','Costa Rica','Cuba','Dominica','Dominican Republic','Ecuador','El Salvador','Grenada','Guatemala','Guyana','Haiti','Honduras','Jamaica','Mexico','Nicaragua','Panama','Paraguay','Peru','Saint Kitts and Nevis','Saint Lucia','Saint Vincent and the Grenadines','Suriname','Trinidad and Tobago','United States','Uruguay','Venezuela'}
AF = {'Algeria','Angola','Benin','Botswana','Burkina Faso','Burundi','Cameroon','Cape Verde','Central African Republic','Chad','Comoros','Congo','DR Congo','Djibouti','Egypt','Equatorial Guinea','Eritrea','Ethiopia','Gabon','Gambia','Ghana','Guinea','Guinea-Bissau','Ivory Coast','Kenya','Lesotho','Liberia','Libya','Madagascar','Malawi','Mali','Mauritania','Mauritius','Morocco','Mozambique','Namibia','Niger','Nigeria','Rwanda','Sao Tome and Principe','Senegal','Seychelles','Sierra Leone','Somalia','South Africa','South Sudan','Sudan','Swaziland','Tanzania','Togo','Tunisia','Uganda','Zambia','Zimbabwe'}
OC = {'Australia','Fiji','Kiribati','Marshall Islands','Micronesia','Nauru','New Zealand','Palau','Papua New Guinea','Samoa','Solomon Islands','Tonga','Tuvalu','Vanuatu'}


def region(c):
    if c in EU: return 'EU'
    if c in AS: return 'AS'
    if c in AM: return 'AM'
    if c in AF: return 'AF'
    if c in OC: return 'OC'
    return 'AS'


def is_open(req):
    req = req.strip().lower()
    if req in ('visa free', 'visa on arrival', 'eta'):
        return True
    try:
        int(req)
        return True
    except ValueError:
        return False


def js_str(s):
    return json.dumps(s, ensure_ascii=False)


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUT

    with open('passport-index-matrix-iso2.csv') as f:
        iso_header = f.readline().strip().split(',')[1:]
    with open('passport-index-matrix.csv') as f:
        name_header = f.readline().strip().split(',')[1:]
    name2iso = dict(zip(name_header, iso_header))

    def flag(iso2):
        if not iso2 or len(iso2) != 2:
            return '\U0001F3F3'
        return chr(0x1F1E6 + ord(iso2[0].upper()) - ord('A')) + \
               chr(0x1F1E6 + ord(iso2[1].upper()) - ord('A'))

    access = {}
    all_dests = set()
    with open('passport-index-tidy.csv') as f:
        for r in csv.DictReader(f):
            p, d, req = r['Passport'], r['Destination'], r['Requirement']
            all_dests.add(d)
            if p == d:
                access.setdefault(p, set()).add(d)
                continue
            if is_open(req):
                access.setdefault(p, set()).add(d)
    for p in list(access):
        access[p].add(p)

    # access_count[d] = how many passports admit destination d visa-free.
    access_count = {}
    for p, acc in access.items():
        for d in acc:
            access_count[d] = access_count.get(d, 0) + 1
    total_passports = len(access)

    lines = []
    w = lines.append
    w("// Open Door Index data — generated from passport-index-tidy.csv (199x199).")
    w("// Build: python3 build_open_door_data.py (in passport-index-dataset).")
    w("// Fields per destination D[name]:")
    w("//   v        incoming intl tourist arrivals, millions/yr (UNWTO)")
    w("//   out      outbound intl departures, millions/yr (UNWTO/World Bank); null = no series")
    w("//   ac       how many of the 199 passports it admits visa-free (its hospitality)")
    w("//   region   EU|AS|AM|AF|OC ; flag ; disputed (true = render gray, out of politics)")
    w("// Per passport: access set, totalM (tourism-weighted reach), top (notable access),")
    w("// rank, hospitality balance, net-tourism balance — see the three maps on the page.")
    w("")
    w("window.PASSPORT_DATA = (() => {")
    w("  const REGIONS = { EU: 'Europe', AS: 'Asia', AM: 'Americas', AF: 'Africa', OC: 'Oceania' };")
    w("")
    w("  const D = {")
    for d in sorted(all_dests):
        v = TOURISM.get(d, 0)
        out = OUTBOUND.get(d)
        out_js = 'null' if out is None else repr(out)
        iso = name2iso.get(d, '')
        ac = access_count.get(d, 0)
        disp = ', disputed: true' if d in DISPUTED else ''
        w(f"    {js_str(d)}: {{ v: {v}, out: {out_js}, region: {js_str(region(d))}, "
          f"flag: {js_str(flag(iso))}, ac: {ac}{disp} }},")
    w("  };")
    w("")
    w(f"  const TOTAL_PASSPORTS = {total_passports};")
    w("")
    w("  const PASSPORTS = [")
    for p in sorted(access.keys()):
        iso = name2iso.get(p, '')
        reg = region(p)
        pop = POP.get(p, 5.0)
        acc_list = sorted(access[p])
        acc_js = '[' + ','.join(js_str(d) for d in acc_list) + ']'
        disp = ', disputed: true' if p in DISPUTED else ''
        w(f"    {{ name: {js_str(p)}, flag: {js_str(flag(iso))}, region: {js_str(reg)}, "
          f"code: {js_str(iso)}, pop: {pop}{disp}, access: new Set({acc_js}) }},")
    w("  ];")
    w("")
    w(COMPUTE_BLOCK)

    text = "\n".join(lines) + "\n"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w') as f:
        f.write(text)
    print(f"Wrote {out_path}")
    print(f"  passports={total_passports} destinations={len(all_dests)}")
    print(f"  outbound series for {len(OUTBOUND)} markets; disputed={sorted(DISPUTED)}")


COMPUTE_BLOCK = r"""  PASSPORTS.forEach(p => {
    let total = 0;
    p.access.forEach(d => { if (D[d]) total += D[d].v; });
    p.totalM = Math.round(total * 10) / 10;
    p.vfCount = p.access.size;
    p.perCapita = Math.round((p.totalM / p.pop) * 10) / 10;

    // NOTABLE ACCESS — destinations that are valuable AND uncommon.
    // Score = visitor_volume × scarcity (= 1 - access_count / total_passports).
    // Skip the passport's home country (everyone has it).
    // Skip destinations with zero or trivial tourism (< 0.5M) so we don't
    // surface obscure islands.
    const scored = [...p.access]
      .filter(d => d !== p.name && D[d] && D[d].v >= 0.5)
      .map(d => {
        const scarcity = 1 - (D[d].ac / TOTAL_PASSPORTS);
        return { name: d, v: D[d].v, score: D[d].v * scarcity };
      })
      .sort((a, b) => b.score - a.score);
    p.top = scored.slice(0, 5).map(x => x.name);
  });

  PASSPORTS.sort((a,b) => b.totalM - a.totalM);
  const maxReach = PASSPORTS[0] ? PASSPORTS[0].totalM : 1;
  let rank = 0, lastVal = null;
  PASSPORTS.forEach((p, idx) => {
    if (p.totalM !== lastVal) { rank = idx + 1; lastVal = p.totalM; }
    p.rank = rank;
  });
  const rankGroups = {};
  PASSPORTS.forEach(p => {
    if (!rankGroups[p.rank]) rankGroups[p.rank] = [];
    rankGroups[p.rank].push(p);
  });
  PASSPORTS.forEach(p => {
    const grp = rankGroups[p.rank];
    p.tieCount = grp.length;
    p.tiePos = grp.indexOf(p);
    p.tieIsLast = p.tiePos === grp.length - 1;
  });

  // ---- Map 2: HOSPITALITY BALANCE ----------------------------------------
  // welcomesShare  = how many passports a country admits, as a share of all
  //                  (D[name].ac / TOTAL) — how wide it holds its door open.
  // usesShare      = the country's own passport reach, as a share of max reach
  //                  — how much of the world's hospitality it consumes.
  // balance        = welcomesShare - usesShare, in [-1, 1].
  //                  > 0  opens wider than it leans on others  (GREEN)
  //                  < 0  leans on others more than it opens    (RED)
  // Attach to each passport row AND mirror onto D[name] so the map can read
  // it by destination name.
  PASSPORTS.forEach(p => {
    const ac = (D[p.name] && D[p.name].ac) || 0;
    const welcomesShare = ac / TOTAL_PASSPORTS;
    const usesShare = p.totalM / maxReach;
    p.welcomesShare = Math.round(welcomesShare * 1000) / 1000;
    p.usesShare = Math.round(usesShare * 1000) / 1000;
    p.hospBalance = Math.round((welcomesShare - usesShare) * 1000) / 1000;
    if (D[p.name]) D[p.name].hospBalance = p.hospBalance;
  });

  // ---- Map 3: NET TOURISM BALANCE ----------------------------------------
  // net = incoming arrivals (v) - outbound departures (out), millions/yr.
  //   > 0  host nation, more come than leave        (GREEN)
  //   < 0  sending nation, more leave than come      (RED)
  //   out === null  no departures series             (gray "limited data")
  // Mirror onto D[name] and the matching passport row.
  Object.keys(D).forEach(name => {
    const d = D[name];
    if (d.out === null || d.out === undefined) { d.netTourism = null; return; }
    d.netTourism = Math.round((d.v - d.out) * 10) / 10;
  });
  PASSPORTS.forEach(p => {
    const d = D[p.name];
    p.netTourism = d ? d.netTourism : null;
    p.incoming = d ? d.v : 0;
    p.outbound = d ? d.out : null;
  });

  return { PASSPORTS, DESTS: D, REGIONS, TOTAL_PASSPORTS, MAX_REACH: maxReach };
})();"""


if __name__ == '__main__':
    main()
