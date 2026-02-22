"""
Bootstrapper for genai_poc schema - creates tables, loads sample data, applies COMMENT ON metadata.
Sample data is designed to support all 6 golden queries from the customer.
"""
import random
import traceback
from datetime import datetime, timedelta
from .redshift_connector_iam import get_redshift_connection
from .genai_poc_ddl import DDL_STATEMENTS, SCHEMA
from .genai_poc_comments import TABLE_COMMENTS, COLUMN_COMMENTS

# --- Reference data for realistic sample generation ---

LOAN_OFFICERS = [
    "Sarah Johnson", "Michael Chen", "David Williams", "Jennifer Martinez",
    "Robert Taylor", "Lisa Anderson", "James Wilson", "Maria Garcia",
    "John Brown", "Emily Davis"
]

FIRST_NAMES = [
    "Michael", "Michael", "Michael", "Michael", "Michael",  # Ensure enough Michaels for query 6
    "James", "Robert", "John", "David", "William", "Richard", "Joseph",
    "Sarah", "Jennifer", "Linda", "Patricia", "Elizabeth", "Barbara", "Susan",
    "Jessica", "Karen", "Nancy", "Lisa", "Margaret", "Dorothy", "Sandra"
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez",
    "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin"
]

STATES = [
    "IL", "IL", "IL", "IL", "IL",  # Ensure enough IL properties for query 6
    "CA", "TX", "FL", "NY", "PA", "OH", "GA", "NC", "MI", "NJ",
    "VA", "WA", "AZ", "MA", "TN", "IN", "MO", "MD", "WI", "CO"
]

CITIES_BY_STATE = {
    "IL": ["Chicago", "Aurora", "Naperville", "Joliet", "Rockford"],
    "CA": ["Los Angeles", "San Francisco", "San Diego", "Sacramento"],
    "TX": ["Houston", "Dallas", "Austin", "San Antonio"],
    "FL": ["Miami", "Orlando", "Tampa", "Jacksonville"],
    "NY": ["New York", "Buffalo", "Rochester", "Albany"],
    "PA": ["Philadelphia", "Pittsburgh", "Allentown"],
    "OH": ["Columbus", "Cleveland", "Cincinnati"],
    "GA": ["Atlanta", "Savannah", "Augusta"],
    "NC": ["Charlotte", "Raleigh", "Durham"],
    "MI": ["Detroit", "Grand Rapids", "Ann Arbor"],
    "NJ": ["Newark", "Jersey City", "Trenton"],
    "VA": ["Virginia Beach", "Richmond", "Norfolk"],
    "WA": ["Seattle", "Tacoma", "Spokane"],
    "AZ": ["Phoenix", "Tucson", "Mesa"],
    "MA": ["Boston", "Worcester", "Springfield"],
    "TN": ["Nashville", "Memphis", "Knoxville"],
    "IN": ["Indianapolis", "Fort Wayne", "Evansville"],
    "MO": ["Kansas City", "St. Louis", "Springfield"],
    "MD": ["Baltimore", "Annapolis", "Rockville"],
    "WI": ["Milwaukee", "Madison", "Green Bay"],
    "CO": ["Denver", "Colorado Springs", "Aurora"],
}

MORTGAGE_TYPES = ["Conventional", "Conventional", "Conventional", "FHA", "FHA", "VA"]
OCCUPANCY_TYPES = ["PrimaryResidence", "SecondHome", "InvestmentProperty"]
LOAN_PURPOSES = ["Purchase", "Cash-Out Refinance", "NoCash-Out Refinance"]
LOAN_PROGRAMS = [
    "30 Year Fixed", "15 Year Fixed", "30 Year Fixed Jumbo", "15 Year Fixed Jumbo",
    "5/1 ARM", "7/1 ARM", "FHA 30 Year Fixed", "VA 30 Year Fixed",
    "30 Year Fixed Jumbo High Balance", "Jumbo ARM 5/1"
]
CHANNELS = ["Retail", "Wholesale", "Correspondent"]
PROPERTY_TYPES = ["SingleFamily", "Condominium", "Townhouse", "MultiFamily", "PUD"]


def _random_date(start_year=2024, end_year=2025):
    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 12, 31)
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def _generate_loan_number(i):
    return f"LN{2024000000 + i}"


def generate_origination_data(n=100):
    """Generate n origination records using dict-based approach for correctness."""
    rows = []
    for i in range(n):
        loan_num = _generate_loan_number(i)
        mortgage_type = random.choice(MORTGAGE_TYPES)
        loan_program = random.choice(LOAN_PROGRAMS)

        if i < 10:  # Ensure Jumbo loans (query 5)
            mortgage_type = "Conventional"
            loan_program = random.choice(["30 Year Fixed Jumbo", "15 Year Fixed Jumbo", "Jumbo ARM 5/1"])

        funded = _random_date(2025, 2025) if i < 70 else _random_date(2024, 2024)  # query 1

        lo_name = "Sarah Johnson" if i < 20 else random.choice(LOAN_OFFICERS)  # query 1 top LO

        base_amount = round(random.uniform(150000, 900000), 2)
        rate = round(random.uniform(5.5, 7.5), 6)
        ltv = round(random.uniform(60, 97), 4)
        orig_date = _random_date(2024, 2025)

        d = {c: None for c in ORIGINATION_COLS}
        d.update({
            "loannumber": loan_num, "version": 1, "organizationcode": "GR001",
            "originationdate": orig_date, "baseloanamount": base_amount,
            "occupancytype": random.choice(OCCUPANCY_TYPES),
            "loanpurposetype": random.choice(LOAN_PURPOSES),
            "channel": random.choice(CHANNELS), "loanprogramname": loan_program,
            "mortgagetype": mortgage_type, "ltv": ltv,
            "combinedltv": round(ltv + random.uniform(0, 5), 4),
            "requestedinterestratepercent": rate,
            "loanamortizationtermmonths": 360 if "30" in loan_program else 180,
            "purchasepriceamount": round(base_amount * random.uniform(1.0, 1.3), 2),
            "loanamortizationtype": "Fixed" if "Fixed" in loan_program else "AdjustableRate",
            "applicationtakenmethodtype": "FaceToFace",
            "loanstatusdate": orig_date + timedelta(days=random.randint(1, 30)),
            "borrowerrequestedloanamount": base_amount,
            "conformingjumbo": "Jumbo" if "jumbo" in loan_program.lower() else "Conforming",
            "lenderchannel": random.choice(CHANNELS),
            "pmiindicator": random.random() > 0.7,
            "nmlsloanoriginatorid": f"NMLS{random.randint(100000, 999999)}",
            "dtiattimeofctc": round(random.uniform(30, 50), 4),
            "isdigitalmortgage": random.choice(["Y", "N"]),
            "loanfolder": random.choice(["Pipeline", "Funded", "Closed"]),
            "balloonindicator": False, "lienprioritytype": "First",
            "prepaymentpenaltyindicator": False,
            "fundeddate": funded, "milestonename": "Funded",
            "insertdatetime": datetime.now(), "insertuser": "system",
            "istestloan": "N",
            "loanoriginatorfirstname": lo_name.split()[0],
            "loanoriginatorlastname": lo_name.split()[-1],
            "paidloid": f"LO{random.randint(1000, 9999)}",
            "paidloname": lo_name,
            "firsttimehomebuyerindicator": random.random() > 0.7,
            "principalandinterestmonthlypaymentamount": round(base_amount / 360 * (rate / 1200 + 1), 2),
            "proposedmaturityyears": 30 if "30" in loan_program else 15,
            "undiscountedrate": round(rate + 0.25, 6),
            "productdescription": loan_program,
        })
        rows.append(tuple(d[c] for c in ORIGINATION_COLS))
    return rows


def generate_borrower_data(n_loans=100):
    """Generate borrower records - some loans get co-borrowers."""
    rows = []
    for i in range(n_loans):
        loan_num = _generate_loan_number(i)
        first = "Michael" if i < 8 else random.choice(FIRST_NAMES)  # query 6
        last = random.choice(LAST_NAMES)
        fico = random.randint(620, 820)

        d = {c: None for c in BORROWER_COLS}
        # Set all boolean cols to False by default
        for c in BORROWER_COLS:
            if "indicator" in c.lower():
                d[c] = False
        d.update({
            "loannumber": loan_num, "applicationnumber": 1, "borrowernumber": 1, "version": 1,
            "firstname": first, "lastnamewithsuffix": last, "lastname": last,
            "ageatapplication": random.randint(25, 70),
            "experiancreditscore": str(random.randint(600, 820)),
            "hmdagendertype": random.choice(["Male", "Female"]),
            "birthdate": datetime(1960 + random.randint(0, 40), random.randint(1, 12), random.randint(1, 28)),
            "equifaxscore": str(random.randint(600, 820)),
            "transunionscore": str(random.randint(600, 820)),
            "hmdawhiteindicator": True,
            "hmdagendertypemaleindicator": True,
            "hmdaethnicitynothispaniclatinoindicator": True,
            "timeoncurrentjobtermyears": random.randint(1, 20),
            "timeoncurrentjobtermmonths": random.randint(0, 11),
            "ficoscore": fico,
            "insertdatetime": datetime.now(), "insertuser": "system",
            "emailaddress": f"{first.lower()}@example.com",
        })
        rows.append(tuple(d[c] for c in BORROWER_COLS))

        # ~30% get a co-borrower
        if random.random() < 0.3:
            co_first = random.choice(FIRST_NAMES)
            d2 = dict(d)
            d2.update({
                "borrowernumber": 2, "firstname": co_first,
                "lastnamewithsuffix": last, "lastname": last,
                "ageatapplication": random.randint(25, 70),
                "ficoscore": random.randint(620, 820),
                "emailaddress": f"{co_first.lower()}@example.com",
            })
            rows.append(tuple(d2[c] for c in BORROWER_COLS))
    return rows


def generate_property_data(n_loans=100):
    """Generate property records - one per loan."""
    rows = []
    for i in range(n_loans):
        loan_num = _generate_loan_number(i)
        state = "IL" if i < 8 else random.choice(STATES)  # query 6
        city = random.choice(CITIES_BY_STATE.get(state, ["Unknown"]))
        appraised = round(random.uniform(200000, 1200000), 2)

        d = {c: None for c in PROPERTY_COLS}
        d.update({
            "loannumber": loan_num, "version": 1,
            "streetaddress": f"{random.randint(100, 9999)} {random.choice(['Main', 'Oak', 'Elm', 'Maple', 'Cedar'])} St",
            "cityname": city, "statecode": state, "zipcode": f"{random.randint(10000, 99999)}",
            "numberofunits": 1, "propertyrightstype": "Fee Simple",
            "appraisedvalueamount": appraised,
            "estimatedvalueamount": round(appraised * random.uniform(0.9, 1.1), 2),
            "gsepropertytype": random.choice(PROPERTY_TYPES),
            "insertdatetime": datetime.now(), "insertuser": "system",
            "propertyusagetype": random.choice(PROPERTY_TYPES),
            "propertyvaluationdate": _random_date(2024, 2025),
            "county": f"{city} County",
            "lotacres": round(random.uniform(0.1, 5.0), 4),
        })
        rows.append(tuple(d[c] for c in PROPERTY_COLS))
    return rows
    return rows


def _insert_batch(cursor, table, columns, rows, batch_size=50):
    """Insert rows in batches."""
    placeholders = ",".join(["%s"] * len(columns))
    cols_str = ",".join(columns)
    sql = f"INSERT INTO {SCHEMA}.{table} ({cols_str}) VALUES ({placeholders})"
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        cursor.executemany(sql, batch)


ORIGINATION_COLS = [
    "loannumber", "version", "organizationcode", "originationdate", "baseloanamount",
    "occupancytype", "loanpurposetype", "channel", "loanprogramname", "mortgagetype",
    "gserefinancepurposetype", "ltv", "combinedltv", "requestedinterestratepercent",
    "loanamortizationtermmonths", "purchasepriceamount", "loanamortizationtype",
    "secondsubordinateamount", "applicationtakenmethodtype", "loanstatusdate",
    "borrowerrequestedloanamount", "interviewername", "repurchasedate", "repurchasecostamount",
    "conformingjumbo", "lenderchannel", "pmiindicator", "nmlsloanoriginatorid",
    "loansubmittedtobrokerdate", "dtiattimeofctc", "isdigitalmortgage",
    "brokerloanfundeddate", "loanfolder", "filestartername", "balloonindicator",
    "lienprioritytype", "prepaymentpenaltyindicator",
    "subsequentrateadjustmentmonthscount", "loandocumentationtype", "firstchargeamount",
    "closingdate", "transdetailslockdate", "constructionmethodtype", "atrloantype",
    "gseagencyqmstatusinterestonly", "gseagencyqmstatusnegativeamortization",
    "gseagencyqmstatusballoonpayment", "gseagencyqmstatusprepaymentpenalty",
    "statementcreditdenialotherdesc1", "statementcreditdenialotherdesc2",
    "tsumunpaidbalance", "tpocompanyname", "valoancreditscore", "fundeddate",
    "milestonename", "insertdatetime", "insertuser", "istestloan",
    "agencypooluploaddate", "lqa", "lastcompletedmilestone", "entityid",
    "poolnumber", "commitmentnumber", "currentapplicationindex",
    "isliabilitysuspensereason", "loanoriginatorfirstname", "loanoriginatorlastname",
    "paidloid", "paidloname", "adtrack", "firsttimehomebuyerindicator",
    "principalandinterestmonthlypaymentamount", "proposedmaturityyears",
    "proposedtotalhousingexpense", "proposedothermortgagesamount",
    "proposedmortgageinsuranceamount", "proposedrealestatetaxesamount",
    "proposedduesamount", "proposedhazardinsuranceamount",
    "freddiemacnoappraisalmaf", "incomeexpirationvalidationindicator",
    "leadsource", "filestartdate", "creditreportordereddate",
    "borrowercount", "selfemployed", "brokerloanclosedate",
    "complianceteamcomments", "legalholddate", "legalholdreleasedate",
    "batchdelete", "velocifyleadid", "adversesubmissiondate", "adverseactiontype",
    "appraisalexpirationdate", "creditexpirationdate", "ficofirstpulleddate",
    "preapprovalordereddate", "respaapplicationdate", "submittedtoprocessingdate",
    "undiscountedrate", "productdescription", "loanfeaturesotherindicator",
    "freddiemacincomebaseddeedrestrictions", "guaranteefeeborrowerpaidamount",
    "refinanceoriginalcreditorindicator", "commercialloanproducttype",
    "commercialloanproducttypeother", "costcenterchargebacklo", "leadsourcebrco"
]

BORROWER_COLS = [
    "loannumber", "applicationnumber", "borrowernumber", "version",
    "firstname", "lastnamewithsuffix", "lastname", "ageatapplication",
    "experiancreditscore", "ssn", "hmdagendertype", "birthdate",
    "equifaxscore", "transunionscore", "hmdaethnicitytype",
    "hmdaamericanindianindicator", "hmdaasianindicator",
    "hmdaafricanamericanindicator", "hmdapacificislanderindicator",
    "hmdawhiteindicator", "hmdanotprovidedindicator",
    "hmdanotapplicableindicator", "hmdanocoapplicantindicator",
    "isethnicitybasedonvisual", "isracebasedonvisual", "issexbasedonvisual",
    "hmdaotherhispaniclatinoorigin", "hmdaamericanindiantribe",
    "hmdaotherasianrace", "hmdaotherpacificislanderrace",
    "applicationtakenmethodtype", "hmdamexicanindicator",
    "hmdapuertoricanindicator", "hmdacubanindicator",
    "hmdahispaniclatinootheroriginindicator", "hmdaasianindianindicator",
    "hmdachineseindicator", "hmdafilipinoindicator", "hmdajapaneseindicator",
    "hmdakoreanindicator", "hmdavietnameseindicator",
    "hmdaasianotherraceindicator", "hmdanativehawaiianindicator",
    "hmdaguamanianorchamorroindicator", "hmdasamoanindicator",
    "hmdapacificislanderotherindicator", "hmdagendertypefemaleindicator",
    "hmdagendertypemaleindicator", "hmdagendertypedonotwishindicator",
    "hmdagendertypenotapplicableindicator", "hmdaethnicitydonotwishindicator",
    "hmdaethnicityhispaniclatinoindicator",
    "hmdaethnicitynothispaniclatinoindicator",
    "hmdaethnicitynotapplicableindicator", "hmdaethnicityinfonotprovided",
    "hmdaraceinfonotprovided", "hmdasexinfonotprovided",
    "hmdaracedonotwishprovideindicator",
    "underwritingriskassesstype", "ausrecommendation",
    "timeoncurrentjobtermyears", "timeoncurrentjobtermmonths",
    "timeonpreviousjobtermyears", "timeonpreviousjobtermmonths",
    "currentresidencedurationtermyears", "currentresidencedurationtermmonths",
    "previousresidencedurationtermyears", "previousresidencedurationtermmonths",
    "hmda2creditscorefordecisionmaking", "hmda2creditscoringmodel", "ficoscore",
    "insertdatetime", "insertuser", "middlename", "suffix", "emailaddress",
    "mailingaddressline1", "mailingaddressline2", "mailingaddresscity",
    "mailingaddressstate", "mailingaddresszip",
    "currentaddressline1", "currentaddressline2", "currentaddresscity",
    "currentaddressstate", "currentaddresszip",
    "homephonenumber", "hmdaethnicityreported", "hmdaracereported"
]

PROPERTY_COLS = [
    "loannumber", "version", "streetaddress", "cityname", "statecode", "zipcode",
    "numberofunits", "propertyrightstype", "appraisedvalueamount",
    "estimatedvalueamount", "gsepropertytype", "insertdatetime", "insertuser",
    "propertyusagetype", "propertyvaluationdate", "county", "lotacres",
    "commercialloanproperty", "commercialpropertytype", "commercialpropertytypeother"
]


def check_genai_poc_exists():
    """Check if genai_poc schema exists with data."""
    try:
        conn = get_redshift_connection()
        cur = conn.cursor()
        cur.execute(f"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = '{SCHEMA}' AND table_type = 'BASE TABLE'")
        count = cur.fetchone()[0]
        if count < 3:
            conn.close()
            return False
        cur.execute(f"SELECT COUNT(*) FROM {SCHEMA}.origination_currentversion")
        rows = cur.fetchone()[0]
        conn.close()
        return rows > 0
    except:
        return False


def bootstrap_genai_poc(n_loans=100):
    """Create genai_poc schema, tables, sample data, and COMMENT ON metadata."""
    conn = get_redshift_connection()
    try:
        cur = conn.cursor()

        # 1. Drop and recreate schema
        print(f"Creating schema {SCHEMA}...")
        cur.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
        conn.commit()

        for ddl in DDL_STATEMENTS:
            cur.execute(ddl)
            conn.commit()
        print("Tables created.")

        # 2. Generate and insert sample data
        random.seed(42)  # Reproducible data

        print(f"Generating {n_loans} origination records...")
        orig_rows = generate_origination_data(n_loans)
        _insert_batch(cur, "origination_currentversion", ORIGINATION_COLS, orig_rows)
        conn.commit()
        print(f"Inserted {len(orig_rows)} origination records.")

        print("Generating borrower records...")
        borr_rows = generate_borrower_data(n_loans)
        _insert_batch(cur, "originationborrower_currentversion", BORROWER_COLS, borr_rows)
        conn.commit()
        print(f"Inserted {len(borr_rows)} borrower records.")

        print("Generating property records...")
        prop_rows = generate_property_data(n_loans)
        _insert_batch(cur, "originationproperty_currentversion", PROPERTY_COLS, prop_rows)
        conn.commit()
        print(f"Inserted {len(prop_rows)} property records.")

        # 3. Apply COMMENT ON TABLE
        print("Applying table comments...")
        for table, comment in TABLE_COMMENTS.items():
            cur.execute(f"COMMENT ON TABLE {SCHEMA}.{table} IS %s", (comment,))
        conn.commit()

        # 4. Apply COMMENT ON COLUMN
        print("Applying column comments...")
        for table, cols in COLUMN_COMMENTS.items():
            for col, comment in cols.items():
                try:
                    cur.execute(f"COMMENT ON COLUMN {SCHEMA}.{table}.{col} IS %s", (comment,))
                except Exception as e:
                    print(f"  Warning: Could not comment {table}.{col}: {e}")
                    conn.rollback()
        conn.commit()

        conn.close()
        print(f"\n✅ genai_poc schema bootstrapped successfully!")
        return True

    except Exception as e:
        conn.close()
        print(f"❌ Error: {e}")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    import os
    os.environ['REDSHIFT_HOST'] = 'redshift-cluster-amazon-q2.cwtsoujhoswf.us-east-1.redshift.amazonaws.com'
    os.environ['REDSHIFT_DATABASE'] = 'dev'
    os.environ['REDSHIFT_USER'] = 'awsuser'
    os.environ['REDSHIFT_PASSWORD'] = 'Awsuser12345'
    os.environ['REDSHIFT_SSL_MODE'] = 'require'
    from redshift_connector_iam import _reset_pool
    _reset_pool()
    bootstrap_genai_poc(100)
