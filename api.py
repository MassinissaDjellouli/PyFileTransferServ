from fastapi import FastAPI,HTTPException
import time
import base64
import os
import random
from datetime import datetime
from shutil import make_archive,copy2,rmtree
from distutils.dir_util import copy_tree
from threading import Thread
from concurrent.futures import ThreadPoolExecutor

app = FastAPI()

class Data:
    chunkQueue = {}
    filesInDl = []

data = Data()
def downloadFilesInChunks(paths,requestId):
    data.chunkQueue[requestId] = []
    file = ""
    if len(paths) > 1: file =base64.b85encode(getMultiple(paths))
    else: file = base64.b85encode(getSingle(paths[0]))
    chunkSize = 100000
    chunks = [file[i:i+chunkSize] for i in range(0, len(file), chunkSize)]
    data.filesInDl.remove(paths)
    data.chunkQueue[requestId] = chunks


@app.get("/getList/{path}")
def getFileList(path:str):
    path = path.replace("__separator__","/")
    if(not os.path.exists(path) or os.path.isfile(path)):
        raise HTTPException(404,"This directory does not exist")
    list = []
    content = os.listdir(path)
    for i in content:
        dict = {}
        dict["name"] = i
        dict["type"] = "dir" if os.path.isdir(f"{path}{i}") else "file"
        list.append(dict)
    return list
    
@app.get("/readyToSend/{requestId}")
def readyToSend(requestId:int):
    if requestId in data.chunkQueue and len(data.chunkQueue[requestId]) > 0:
        return {"size": len(data.chunkQueue[requestId])}
    return {"size":-1}
@app.get("/getNextChunk/{requestId}")
def getChunk(requestId:int):
    if requestId not in data.chunkQueue:
        raise HTTPException(404,"This request does not exist")
    return data.chunkQueue[requestId].pop(0)

@app.get("/downloadFiles/{paths}")
def downloadFiles(paths:str):
    paths = paths.replace("__separator__","/")
    paths = paths.split("+")
    size = 0
    if paths in data.filesInDl:
        raise HTTPException(401,"These files are already being downloaded.")
    for path in paths:
        if(not os.path.exists(path)):
            print(path)
            print(not os.path.exists("/Users/massi_hz41cpc/Desktop/session 5/Obj connectés.zip"))
            print(not os.path.exists(path))
            raise HTTPException(404,"This directory or file does not exist")
        size += get_size(path) if os.path.isdir(path) else os.path.getsize(path)
    if(size > 10000000):
        data.filesInDl += [paths]
        requestId = time.time_ns()
        Thread(target=downloadFilesInChunks,args=(paths,requestId)).start()
        if len(paths) > 1: toReturn = {"name":"archive.zip","requestId":requestId}
        else: toReturn = {"name":paths[0].split("/")[-1],"requestId":requestId}
        return toReturn
    if len(paths) > 1: toReturn = {"name":"archive.zip","file":base64.b85encode(getMultiple(paths))}
    else: toReturn = {"name":paths[0].split("/")[-1],"file":base64.b85encode(getSingle(paths[0]))}
    return toReturn
        


def getMultiple(paths):
    #get the common directory of all the files
    commonDir = os.path.commonpath(paths)
    while not os.path.isdir(commonDir):
        commonDir = commonDir[:commonDir.rfind("/")]

    temp = f"{commonDir}temp_{time.time_ns()}_{random.randint(1,255)}"
    tempDirName = f"{temp}/temp"
    try:
        os.mkdir(temp)
        os.mkdir(tempDirName)
        for path in paths:
            if(not os.path.exists(path)):
                raise HTTPException(404,"This directory or file does not exist")
            #get the name of the file or directory to copy it to the temp directory
            name = path.split("/")[-1]
            if os.path.isdir(path):
                copy_tree(path,f"{tempDirName}/{name}")
            else:
                copy2(path,f"{tempDirName}/{name}")
        archive = make_archive(f"{temp}/archive_{datetime.now().strftime('%d_%m_%Y+%H_%M_%S')}","zip",tempDirName)
        print(archive)
        content = []
        with open(archive,"rb") as file:
            content = file.read()
        rmtree(temp)
        return content
    except Exception as e:
        print(e)
        raise HTTPException(401,"These files cannot be downloaded.")


def get_size(start_path = '.'):
    total_size = 0
    amountOfFiles = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        amountOfFiles += 1
        if(amountOfFiles > 1000):
            raise HTTPException(401,"Too much files.")
        for f in filenames:
            fp = os.path.join(dirpath, f)
            # skip if it is symbolic link
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)
    return total_size

def getSingle(path):
    if(not os.path.exists(path)):
        raise HTTPException(404,"This directory does not exist")
    if(os.path.isdir(path)):
        return getMultiple([path])
    with open(path,"rb") as file:
        return file.read()