# 발표용 준비사항 (12/8)

배포하지 않고 발표자 컴퓨터 한 대에서 서버를 실행해 데모한다. 발표 전에 아래를 준비한다.

## 1. 데모 사진

- 업로드한 사진은 서버를 실행한 컴퓨터의 `apps/fe/static/uploads/`에만 저장된다. Firebase에는 파일명(`img_path`)만 저장된다.
- [ ] 데모에 쓸 상품 사진을 정한다. (JPG, PNG, 5MB 이하)
- [ ] `apps/fe/static/uploads/`를 `.gitignore`에 추가한다.
- [ ] 데모 사진만 `git add -f`로 커밋해서 모든 팀원 화면에서 보이게 한다.

## 2. 데모 데이터

- [ ] Firebase의 테스트 데이터를 삭제한다. (11/22에 등록한 `맥북 에어 M2`, `자료구조 전공책`, `아이패드 1/2` 포함)
- [ ] 데모 계정을 만든다. (판매자 1명, 구매자 1명 이상)
- [ ] 데모 상품을 등록한다. 가격 정해진 상품, 경매 상품, 거래 완료 상품을 각각 1개 이상 준비한다.
- [ ] 데모 시나리오 순서대로 한 번 실행해서 필요한 데이터가 모두 있는지 확인한다.

## 3. 메일 인증

- [ ] 발송용 Gmail 계정을 만든다. (후보: `boughtit.ewha@gmail.com`)
- [ ] 2단계 인증을 설정하고 앱 비밀번호를 발급한다.
- [ ] 발표자 컴퓨터에 환경 변수 `MAIL_USER`, `MAIL_PASSWORD`를 설정한다.
- [ ] 실제 이화인 메일로 인증 코드가 도착하는지 확인한다.

## 4. 발표자 컴퓨터

- [ ] `authentication/firebase_auth.json`이 있는지 확인한다.
- [ ] `pip install -r apps/be/requirements.txt` 후 `python apps/be/app.py`로 실행되는지 확인한다.
- [ ] 발표장 네트워크에서 Firebase와 Gmail SMTP에 연결되는지 확인한다. 연결되지 않을 때를 대비해 녹화본을 준비한다.

## 5. 정리

- [ ] `test-data/` 폴더와 `apps/be/test_product.py`를 남길지 정한다.
