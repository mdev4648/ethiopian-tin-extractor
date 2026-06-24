# from fastapi import FastAPI, UploadFile, File
# from fastapi.responses import FileResponse
# from fastapi.templating import Jinja2Templates
# from fastapi.requests import Request

# import pandas as pd
# import requests
# import uuid
# import os

# app = FastAPI()

# templates = Jinja2Templates(directory="templates")

# UPLOAD_DIR = "uploads"
# OUTPUT_DIR = "outputs"

# os.makedirs(UPLOAD_DIR, exist_ok=True)
# os.makedirs(OUTPUT_DIR, exist_ok=True)


# # @app.get("/")
# # async def home(request: Request):
# #     return templates.TemplateResponse(
# #         "index.html",
# #         {"request": request}
# #     )
# @app.get("/")
# async def home(request: Request):
#     return templates.TemplateResponse(
#         request=request,
#         name="index.html",
#         context={}
#     )

# @app.post("/extract-mobile")
# async def extract_mobile(
#     request: Request,
#     file: UploadFile = File(...)
# ):

#     filename = f"{uuid.uuid4()}.xlsx"
#     filepath = os.path.join(
#         UPLOAD_DIR,
#         filename
#     )

#     with open(filepath, "wb") as f:
#         f.write(await file.read())

#     df = pd.read_excel(
#         filepath,
#         dtype={"TIN": str}
#     )

#     results = []

#     for tin in df["TIN"]:

#         tin = str(tin).zfill(10)

#         try:

#             url = (
#                 f"http://erca.gov.et:8003/"
#                 f"taxPayerProfile/api/taxpayers/{tin}"
#             )

#             response = requests.get(
#                 url,
#                 timeout=30
#             )

#             mobile = ""

#             if response.status_code == 200:

#                 data = response.json()

#                 enterprises = data.get(
#                     "Enterprises",
#                     []
#                 )

#                 if enterprises:
#                     mobile = enterprises[0].get(
#                         "MobilePhone",
#                         ""
#                     )

#             results.append({
#                 "TIN": tin,
#                 "MobilePhone": mobile
#             })

#         except:
#             results.append({
#                 "TIN": tin,
#                 "MobilePhone": ""
#             })

#     output_name = f"{uuid.uuid4()}.csv"

#     output_path = os.path.join(
#         OUTPUT_DIR,
#         output_name
#     )

#     pd.DataFrame(results).to_csv(
#         output_path,
#         index=False
#     )

#     return FileResponse(
#         output_path,
#         filename="mobile_numbers.csv"
#     )


# @app.post("/extract-establishments")
# async def extract_establishments(
#     request: Request,
#     file: UploadFile = File(...)
# ):

#     filename = f"{uuid.uuid4()}.xlsx"

#     filepath = os.path.join(
#         UPLOAD_DIR,
#         filename
#     )

#     with open(filepath, "wb") as f:
#         f.write(await file.read())

#     df = pd.read_excel(
#         filepath,
#         dtype={"TIN": str}
#     )

#     results = []

#     total = len(df)

#     for index, tin in enumerate(
#         df["TIN"],
#         start=1
#     ):

#         tin = str(tin).zfill(10)

#         print(
#             f"[{index}/{total}] {tin}"
#         )

#         try:

#             url = (
#                 f"http://erca.gov.et:8003/"
#                 f"taxPayerProfile/api/taxpayers/{tin}"
#             )

#             response = requests.get(
#                 url,
#                 timeout=30
#             )

#             if response.status_code != 200:
#                 continue

#             data = response.json()

#             enterprises = data.get(
#                 "Enterprises",
#                 []
#             )

#             for enterprise in enterprises:

#                 establishments = enterprise.get(
#                     "establishments",
#                     []
#                 )

#                 for est in establishments:

#                     phone = (
#                         est.get(
#                             "address",
#                             {}
#                         ).get(
#                             "PhoneNo"
#                         )
#                     )

#                     name = est.get(
#                         "EstablishmentName"
#                     )

#                     results.append({
#                         "TIN": tin,
#                         "EstablishmentName": name,
#                         "PhoneNo": phone,
#                     })

#         except Exception as e:

#             print(
#                 f"Error {tin}: {e}"
#             )

#     output_name = (
#         f"{uuid.uuid4()}.csv"
#     )

#     output_path = os.path.join(
#         OUTPUT_DIR,
#         output_name
#     )

#     pd.DataFrame(
#         results
#     ).to_csv(
#         output_path,
#         index=False
#     )

#     return FileResponse(
#         output_path,
#         filename="establishments.csv"
#     )

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


def process_mobile_task(task_id: str, filepath: str):
    try:
        df = pd.read_excel(filepath, dtype={"TIN": str})
        results = []
        total = len(df)
        
        tasks_progress[task_id].update({"total": total, "status": "processing"})

        for index, tin in enumerate(df["TIN"], start=1):
            tin_str = str(tin).split('.')[0].zfill(10)  # Safe string formatting
            tasks_progress[task_id].update({"current": index, "current_tin": tin_str})

            try:
                url = f"http://erca.gov.et:8003/taxPayerProfile/api/taxpayers/{tin_str}"
                response = requests.get(url, timeout=20)
                mobile = ""

                if response.status_code == 200:
                    data = response.json()
                    enterprises = data.get("Enterprises", [])
                    if enterprises:
                        mobile = enterprises[0].get("MobilePhone", "")

                results.append({"TIN": tin_str, "MobilePhone": mobile})
            except:
                results.append({"TIN": tin_str, "MobilePhone": ""})

        output_name = f"{uuid.uuid4()}.csv"
        output_path = os.path.join(OUTPUT_DIR, output_name)
        pd.DataFrame(results).to_csv(output_path, index=False)

        tasks_progress[task_id].update({
            "status": "completed", 
            "file_path": output_path, 
            "filename": "mobile_numbers.csv"
        })
    except Exception as e:
        tasks_progress[task_id].update({"status": "failed", "error": str(e)})


def process_establishment_task(task_id: str, filepath: str):
    try:
        df = pd.read_excel(filepath, dtype={"TIN": str})
        results = []
        total = len(df)
        
        tasks_progress[task_id].update({"total": total, "status": "processing"})

        for index, tin in enumerate(df["TIN"], start=1):
            tin_str = str(tin).split('.')[0].zfill(10)
            tasks_progress[task_id].update({"current": index, "current_tin": tin_str})

            try:
                url = f"http://erca.gov.et:8003/taxPayerProfile/api/taxpayers/{tin_str}"
                response = requests.get(url, timeout=20)

                if response.status_code != 200:
                    continue

                data = response.json()
                enterprises = data.get("Enterprises", [])
                LegalName=data.get("LegalName")
                results.append({
                            "Legal Name": LegalName,
                        })

                for enterprise in enterprises:
                    establishments = enterprise.get("establishments", [])
                    TradeName=enterprise.get("TradeName")
                    results.append({
                            "Trade Name": TradeName,
                        })
                    for est in establishments:
                        phone = est.get("address", {}).get("PhoneNo", "")
                        name = est.get("EstablishmentName", "")
                        establishmentNumber=est.get("EstablishmentNumber", "")
                        results.append({
                            "TIN": tin_str,
                            "EstablishmentName": name,
                            "Establishment Number":establishmentNumber,
                            "PhoneNo": phone,
                        })
            except Exception as e:
                print(f"Error checking {tin_str}: {e}")

        output_name = f"{uuid.uuid4()}.csv"
        output_path = os.path.join(OUTPUT_DIR, output_name)
        pd.DataFrame(results).to_csv(output_path, index=False)

        tasks_progress[task_id].update({
            "status": "completed", 
            "file_path": output_path, 
            "filename": "establishments.csv"
        })
    except Exception as e:
        tasks_progress[task_id].update({"status": "failed", "error": str(e)})


@app.post("/extract-mobile")
async def extract_mobile(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    task_id = str(uuid.uuid4())
    filename = f"{task_id}.xlsx"
    filepath = os.path.join(UPLOAD_DIR, filename)

    with open(filepath, "wb") as f:
        f.write(await file.read())

    tasks_progress[task_id] = {"status": "pending", "current": 0, "total": 0, "current_tin": ""}
    background_tasks.add_task(process_mobile_task, task_id, filepath)
    
    return {"task_id": task_id}


@app.post("/extract-establishments")
async def extract_establishments(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    task_id = str(uuid.uuid4())
    filename = f"{task_id}.xlsx"
    filepath = os.path.join(UPLOAD_DIR, filename)

    with open(filepath, "wb") as f:
        f.write(await file.read())

    tasks_progress[task_id] = {"status": "pending", "current": 0, "total": 0, "current_tin": ""}
    background_tasks.add_task(process_establishment_task, task_id, filepath)
    
    return {"task_id": task_id}


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