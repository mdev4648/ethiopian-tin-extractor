from fastapi import FastAPI, UploadFile, File, BackgroundTasks, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

import pandas as pd
import requests
import uuid
import os

app = FastAPI()

# Mount static folder directory for the CSS file
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

UPLOAD_DIR = "uploads"
OUTPUT_DIR = "outputs"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Shared dictionary structure tracking task states in memory
tasks_progress = {}

@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


# def process_establishment_task(task_id: str, filepath: str):
#     try:
#         df = pd.read_excel(filepath, dtype={"TIN": str})
#         results = []
#         total = len(df)
        
#         tasks_progress[task_id].update({"total": total, "status": "processing"})

#         for index, tin in enumerate(df["TIN"], start=1):
#             tin_str = str(tin).split('.')[0].zfill(10)
#             tasks_progress[task_id].update({"current": index, "current_tin": tin_str})

#             try:
#                 url = f"http://erca.gov.et:8003/taxPayerProfile/api/taxpayers/{tin_str}"
#                 response = requests.get(url, timeout=20)

#                 if response.status_code != 200:
#                     continue

#                 data = response.json()
#                 enterprises = data.get("Enterprises", [])
#                 LegalName=data.get("LegalName")
#                 results.append({
#                             "Legal Name": LegalName,
#                         })

#                 for enterprise in enterprises:
#                     establishments = enterprise.get("establishments", [])
#                     tradeName=enterprise.get("TradeName")
#                     emailAccount=enterprise.get("Email")
#                     phoneNumber=enterprise.get("PhoneNo")
#                     mobileNumber=enterprise.get("MobilePhone")
#                     results.append({
#                             "Trade Name": tradeName,
#                             "Email":emailAccount,
#                             "Phone Number":phoneNumber,
#                             "Mobile Number":mobileNumber
#                         })
#                     for est in establishments:
#                         phone = est.get("address", {}).get("PhoneNo", "")
#                         name = est.get("EstablishmentName", "")
#                         establishmentNumber=est.get("EstablishmentNumber", "")
#                         branchEmailAccount=enterprise.get("Email")
#                         results.append({
#                             "TIN": tin_str,
#                             "EstablishmentName": name,
#                             "Establishment Number":establishmentNumber,
#                             "Branch Email":branchEmailAccount,
#                             "Branch Phone Number": phone,
#                         })
#             except Exception as e:
#                 print(f"Error checking {tin_str}: {e}")

#         output_name = f"{uuid.uuid4()}.csv"
#         output_path = os.path.join(OUTPUT_DIR, output_name)
#         pd.DataFrame(results).to_csv(output_path, index=False)

#         tasks_progress[task_id].update({
#             "status": "completed", 
#             "file_path": output_path, 
#             "filename": "establishments.csv"
#         })
#     except Exception as e:
#         tasks_progress[task_id].update({"status": "failed", "error": str(e)})
def process_establishment_task(task_id: str, filepath: str):
    results = []
    output_name = f"{uuid.uuid4()}.csv"
    output_path = os.path.join(OUTPUT_DIR, output_name)
    
    try:
        df = pd.read_excel(filepath, dtype={"TIN": str})
        total = len(df)
        
        tasks_progress[task_id].update({
            "total": total, 
            "status": "processing",
            "failed_count": 0
        })

        for index, tin in enumerate(df["TIN"], start=1):
            tin_str = str(tin).split('.')[0].strip().zfill(10)
            tasks_progress[task_id].update({"current": index, "current_tin": tin_str})

            try:
                url = f"http://erca.gov.et:8003/taxPayerProfile/api/taxpayers/{tin_str}"
                response = requests.get(url, timeout=30)

                if response.status_code != 200:
                    # Log failed attempts visibly for the UI counter
                    current_failed = tasks_progress[task_id].get("failed_count", 0) + 1
                    tasks_progress[task_id].update({"failed_count": current_failed})
                    continue

                data = response.json()
                legal_name = data.get("legalName", "")
                enterprises = data.get("Enterprises", [])

                results.append({
                            "Legal Name": legal_name,
                        })

                if not enterprises:
                    # Keep track of records that exist but have no enterprise entries
                    results.append({
                        "TIN": tin_str,
                        "Trade Name": "", 
                        "Email": "",
                        "Phone Number": "", 
                        "Mobile Number": "",
                        "EstablishmentName": "", 
                        "Establishment Number": "",
                        "Branch Email": "", 
                        "Branch Phone Number": ""
                    })
                    continue

                for enterprise in enterprises:
                    trade_name = enterprise.get("Trade_name", "")
                    email_account = enterprise.get("address_e_mail", "")
                    phone_number = enterprise.get("phone_no", "")
                    mobile_number = enterprise.get("mobile_phone", "")
                    establishments = enterprise.get("establishments", [])

                    results.append({
                            "Trade Name": trade_name,
                            "Email":email_account,
                            "Phone Number":phone_number,
                            "Mobile Number":mobile_number
                        })


                    for est in establishments:
                        mobile=est.get("address",{}).get("mobile_phone")
                        phone = est.get("address", {}).get("phone_no", "")
                        name = est.get("name", "")
                        # branch_email=est.get("Email"),
                        branch_email = est.get("address", {}).get("address_e_mail", "")
                        establishment_number = est.get("estab_no", "")
                        
                        results.append({
                            "TIN": tin_str,
                            "Establishment Name":name,
                            "Establishment Number": establishment_number,
                            "Branch Email": branch_email,
                            "Branch Phone Number": phone,
                            "Branch Mobile Number":mobile
                        })

            except Exception as e:
                print(f"Network error or request timeout for {tin_str}: {e}")
                current_failed = tasks_progress[task_id].get("failed_count", 0) + 1
                tasks_progress[task_id].update({"failed_count": current_failed})
                # Continue loop processing instead of hard failing right away

        # --- UPDATE THIS BOTTOM SECTION OF YOUR LOOP FUNCTION ---
        
        # If the process finished but absolutely nothing was retrieved and there were failures,
        # it means the internet or API was completely down from the start.
        if len(results) == 0 and tasks_progress[task_id].get("failed_count", 0) > 0:
            tasks_progress[task_id].update({
                "status": "failed",
                "error": "No internet connection or ERCA API is completely unreachable."
            })
            return  # Stop execution here

        # Create output if we at least have partial data
        pd.DataFrame(results).to_csv(output_path, index=False)
        tasks_progress[task_id].update({
            "status": "completed", 
            "file_path": output_path, 
            "filename": "establishments.csv"
        })

    except Exception as general_err:
        print(f"Critical process disruption: {general_err}")
        if results:
            pd.DataFrame(results).to_csv(output_path, index=False)
            tasks_progress[task_id].update({
                "status": "completed", 
                "file_path": output_path, 
                "filename": "establishments_partial.csv",
                "ui_warning": "Process cut short due to network error. Partial data saved."
            })
        else:
            tasks_progress[task_id].update({
                "status": "failed", 
                "error": "Network connection error or process disrupted entirely."
            })

        # Create output even if it contains partial data
        pd.DataFrame(results).to_csv(output_path, index=False)
        tasks_progress[task_id].update({
            "status": "completed", 
            "file_path": output_path, 
            "filename": "establishments.csv"
        })

    # except Exception as general_err:
    #     print(f"Critical process disruption: {general_err}")
    #     # Save whatever records were parsed before the connection went completely dead
    #     if results:
    #         pd.DataFrame(results).to_csv(output_path, index=False)
    #         tasks_progress[task_id].update({
    #             "status": "completed", 
    #             "file_path": output_path, 
    #             "filename": "establishments_partial.csv",
    #             "ui_warning": "Process cut short. Partial data saved."
    #         })
    #     else:
    #         tasks_progress[task_id].update({"status": "failed", "error": str(general_err)})


@app.post("/extract-establishments")
async def extract_establishments(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    task_id = str(uuid.uuid4())
    filename = f"{task_id}.xlsx"
    filepath = os.path.join(UPLOAD_DIR, filename)

    # Save the file temporarily to read it
    with open(filepath, "wb") as f:
        f.write(await file.read())

    # --- NEW EXCEL STRUCTURAL VALIDATION ---
    try:
        # Read only the header row to verify columns quickly
        df_check = pd.read_excel(filepath, nrows=0)
        columns = [str(col).strip() for col in df_check.columns]
        
        if len(columns) != 1 or columns[0] != "TIN":
            os.remove(filepath)  # Clean up the file
            return JSONResponse(
                status_code=400, 
                content={"error": "Invalid file structure. Excel must have exactly one column named 'TIN'."}
            )
    except Exception as e:
        if os.path.exists(filepath):
            os.remove(filepath)
        return JSONResponse(
            status_code=400, 
            content={"error": "Cannot parse Excel file. Please fix data and try again."}
        )
    # --- END OF VALIDATION ---

    tasks_progress[task_id] = {"status": "pending", "current": 0, "total": 0, "current_tin": ""}
    background_tasks.add_task(process_establishment_task, task_id, filepath)
    
    return {"task_id": task_id}

# @app.post("/extract-establishments")
# async def extract_establishments(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
#     task_id = str(uuid.uuid4())
#     filename = f"{task_id}.xlsx"
#     filepath = os.path.join(UPLOAD_DIR, filename)

#     with open(filepath, "wb") as f:
#         f.write(await file.read())

#     tasks_progress[task_id] = {"status": "pending", "current": 0, "total": 0, "current_tin": ""}
#     background_tasks.add_task(process_establishment_task, task_id, filepath)
    
#     return {"task_id": task_id}


@app.get("/task-status/{task_id}")
async def get_status(task_id: str):
    task = tasks_progress.get(task_id)
    if not task:
        return JSONResponse(status_code=404, content={"error": "Task context parameters not found"})
    return task


@app.get("/download/{task_id}")
async def download_file(task_id: str):
    task = tasks_progress.get(task_id)
    if task and task.get("status") == "completed":
        return FileResponse(task["file_path"], filename=task["filename"])
    return JSONResponse(status_code=400, content={"error": "File parsing output not ready"})