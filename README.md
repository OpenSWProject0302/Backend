# 🎼 Easheet – 음원 분석 기반 드럼 악보 자동 생성 서비스

Easheet는 사용자가 업로드한 **음원(WAV)을 자동으로 분석하여 드럼 악보(PDF/MIDI)를 생성하는 웹 서비스**입니다.  
장르 선택 → 음원 업로드 → 악보 생성까지 모든 프로세스를 웹에서 간편하게 수행할 수 있으며, 복잡한 음원 분리와 MIDI·악보 변환은 서버에서 비동기로 처리됩니다.

---

## 📌 주요 기능 (Key Features)

### ✅ 1. 장르 선택 기반 분석 파라미터 적용
- 프론트에서 다양한 장르 카드 UI 제공 (Ballad, Jazz, Rock 등)  
- 선택된 장르에 따라 드럼 패턴 분석 및 출력 결과 최적화

### ✅ 2. 음원 업로드 (AWS S3 Presigned URL)
- 프론트가 백엔드로 **presigned URL 요청**
- 백엔드가 S3 업로드 URL을 생성해 프론트에 전달
- 프론트는 해당 URL로 음원을 안전하게 업로드 (서버를 거치지 않음)

### ✅ 3. 음원 분리 및 드럼 분석
- **Demucs 기반 음원 분리 (Source Separation)**
- **Librosa** 기반 템포/비트 분석  
- 신호 처리 기반 **Drum hit detection → MIDI 변환**
- **Music21**으로 MIDI → MusicXML 변환  
- **MuseScore CLI**로 MusicXML → PDF 악보 렌더링

### ✅ 4. 비동기 작업 처리 (Async Processing)
- Django REST API + Celery + Redis 조합  
- `/process` 요청 → Celery Queue에 작업 등록  
- Worker가 S3에서 음원을 다운로드하여 분석 수행  
- 작업 상태(`PENDING`, `RUNNING`, `DONE`, `ERROR`)는 폴링으로 조회 가능

### ✅ 5. 결과물 다운로드 지원
- PDF, MIDI, MusicXML, Guide Audio 등 결과물을 S3에 업로드  
- 프론트가 `/result` API를 통해 다운로드 URL을 제공받아 표시

---

## 🏗️ 시스템 아키텍처

```mermaid
flowchart TD

    User["사용자<br/>- 장르/난이도 선택<br/>- WAV 업로드"] --> FE["Frontend<br/>(React @ Vercel)"]

    FE -->|Presigned URL 요청| BE_Presign["Django API<br/>/api/uploads/presign"]
    BE_Presign --> FE

    FE -->|WAV 업로드| S3_Input["AWS S3<br/>Input Bucket"]

    FE -->|/api/drums/process| BE_Process["Django API<br/>DrumJob 생성(PENDING)"]

    BE_Process -->|작업 메시지| Redis["Redis<br/>(Message Broker)"]

    Redis --> Worker["Celery Worker (EC2)<br/>WAV 다운로드·분석·변환"]

    Worker -->|결과 업로드| S3_Output["AWS S3<br/>MIDI / PDF / Guide"]

    Worker -->|상태 업데이트| DB["SQLite DB"]

    FE -->|/api/drums/status| BE_Status["Django API<br/>Status 조회"]
    BE_Status --> FE
````

---

## 🗂️ API Overview

### ▶ `/api/uploads/presign`

WAV 파일 업로드용 S3 presigned URL 발급

### ▶ `/api/drums/process`

업로드된 S3 입력 파일 기반 드럼 악보 생성 작업 시작

### ▶ `/api/drums/status/<job_id>`

비동기 작업 상태 조회

### ▶ `/api/drums/result/<job_id>`

PDF, MIDI, MusicXML 파일 다운로드 URL 반환

---

## ⚙️ 기술 스택

### **Frontend**

* React (Vercel 배포)
* Styled Components / CSS
* 브라우저 내장 **fetch API**를 이용한 HTTP 통신
* AWS S3 Presigned Upload

### **Backend**

* Django REST Framework
* Celery + Redis
* Demucs / Librosa / Mido
* Music21 / MuseScore
* AWS S3 (Input/Output)

### **Infrastructure**

* AWS EC2 (Ubuntu, Celery Worker + Django API)
* AWS S3 (파일 저장)
* Vercel (Frontend Hosting)

---

## 👥 Contributors

* 2023112497 강명수
* 2022113287 세바라
* 2022111915 이경훈
* 2023112474 이하늘
* 2022113286 페이자
* 2023112393 한수민

---

## 📑 라이선스 정보 (Library Licenses)

본 프로젝트는 아래의 오픈소스 라이브러리를 사용하며, 모두 **상업적/비상업적 이용이 가능한 Permissive License**를 따릅니다.

### 🧩 사용 라이브러리 및 라이선스

| 라이브러리         | 라이선스         |
| ------------- | ------------ |
| **librosa**   | ISC          |
| **mido**      | MIT          |
| **demucs**    | MIT          |
| **soundfile** | BSD 3-Clause |

---

### 📘 라이선스별 권한 및 의무

| License          | 무료 이용 | 배포 | 수정 | 2차 저작물 공개 의무 | 저작권/라이선스 표시     |
| ---------------- | ----- | -- | -- | ------------ | --------------- |
| **ISC**          | O     | O  | O  | X            | O               |
| **MIT**          | O     | O  | O  | X            | O               |
| **BSD 3-Clause** | O     | O  | O  | X            | O (광고 금지 조항 포함) |

---

### 📚 용어 설명

| 항목                 | 설명                                     |
| ------------------ | -------------------------------------- |
| **무료 사용**          | 상업적/비상업적 목적 모두 포함해 비용 없이 사용할 수 있는지 여부  |
| **배포 가능**          | 라이브러리를 포함한 소프트웨어를 다른 사람에게 전달할 수 있는지 여부 |
| **소스코드 수정 가능**     | 원본 코드를 자유롭게 편집하거나 재구성할 수 있는지 여부        |
| **2차 저작물 공개 의무**   | 수정 결과물을 새 오픈소스로 공개해야 하는지 여부 (해당 없음)    |
| **저작권/라이선스 표시 필요** | 소프트웨어 배포 시 라이선스 문구를 포함해야 함             |

