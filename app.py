from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request

import pandas as pd
import requests
import uuid
import os

app = FastAPI()

templates = Jinja2Templates(directory="templates")

UPLOAD_DIR = "uploads"
OUTPUT_DIR = "outputs"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


# @app.get("/")
# async def home(request: Request):
#     return templates.TemplateResponse(
#         "index.html",
#         {"request": request}
#     )
@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={}
    )

@app.post("/extract-mobile")
async def extract_mobile(
    request: Request,
    file: UploadFile = File(...)
):

    filename = f"{uuid.uuid4()}.xlsx"
    filepath = os.path.join(
        UPLOAD_DIR,
        filename
    )

    with open(filepath, "wb") as f:
        f.write(await file.read())

    df = pd.read_excel(
        filepath,
        dtype={"TIN": str}
    )

    results = []

    for tin in df["TIN"]:

        tin = str(tin).zfill(10)

        try:

            url = (
                f"http://erca.gov.et:8003/"
                f"taxPayerProfile/api/taxpayers/{tin}"
            )

            response = requests.get(
                url,
                timeout=30
            )

            mobile = ""

            if response.status_code == 200:

                data = response.json()

                enterprises = data.get(
                    "Enterprises",
                    []
                )

                if enterprises:
                    mobile = enterprises[0].get(
                        "MobilePhone",
                        ""
                    )

            results.append({
                "TIN": tin,
                "MobilePhone": mobile
            })

        except:
            results.append({
                "TIN": tin,
                "MobilePhone": ""
            })

    output_name = f"{uuid.uuid4()}.csv"

    output_path = os.path.join(
        OUTPUT_DIR,
        output_name
    )

    pd.DataFrame(results).to_csv(
        output_path,
        index=False
    )

    return FileResponse(
        output_path,
        filename="mobile_numbers.csv"
    )


@app.post("/extract-establishments")
async def extract_establishments(
    request: Request,
    file: UploadFile = File(...)
):

    filename = f"{uuid.uuid4()}.xlsx"

    filepath = os.path.join(
        UPLOAD_DIR,
        filename
    )

    with open(filepath, "wb") as f:
        f.write(await file.read())

    df = pd.read_excel(
        filepath,
        dtype={"TIN": str}
    )

    results = []

    total = len(df)

    for index, tin in enumerate(
        df["TIN"],
        start=1
    ):

        tin = str(tin).zfill(10)

        print(
            f"[{index}/{total}] {tin}"
        )

        try:

            url = (
                f"http://erca.gov.et:8003/"
                f"taxPayerProfile/api/taxpayers/{tin}"
            )

            response = requests.get(
                url,
                timeout=30
            )

            if response.status_code != 200:
                continue

            data = response.json()

            enterprises = data.get(
                "Enterprises",
                []
            )

            for enterprise in enterprises:

                establishments = enterprise.get(
                    "establishments",
                    []
                )

                for est in establishments:

                    phone = (
                        est.get(
                            "address",
                            {}
                        ).get(
                            "PhoneNo"
                        )
                    )

                    name = est.get(
                        "EstablishmentName"
                    )

                    results.append({
                        "TIN": tin,
                        "EstablishmentName": name,
                        "PhoneNo": phone,
                    })

        except Exception as e:

            print(
                f"Error {tin}: {e}"
            )

    output_name = (
        f"{uuid.uuid4()}.csv"
    )

    output_path = os.path.join(
        OUTPUT_DIR,
        output_name
    )

    pd.DataFrame(
        results
    ).to_csv(
        output_path,
        index=False
    )

    return FileResponse(
        output_path,
        filename="establishments.csv"
    )