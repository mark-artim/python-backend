from pymongo import MongoClient
import os

def get_active_companies():
    client = MongoClient(os.getenv("MONGO_URI"))
    db = client["emp54"]  # or your actual DB name
    companies = db.companies.find({})
    
    result = []
    for company in companies:
        result.append({
            "name": company.get("name"),
            "code": company.get("companyCode"),
            "wasabiPrefix": company.get("wasabiPrefix", company.get("companyCode")),
            "alertEmail": company.get("alertEmail", "mark.artim@heritagedistribution.com")
        })
    return result
