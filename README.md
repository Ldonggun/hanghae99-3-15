# 항해99 3기 15조: '연수구 가치봉사'
나만의 봉사 활동 page를 관리하고 싶지 않으신가요? 저희 사이트는 인천 연수구 가치 봉사 사이트는 현재 모집중인 봉사활동 리스트와 상세페이지를 제공합니다. Mypage에서 관심있는 봉사활동을 스크랩하고 완료 시간도 체크해 보세요!
<br>
<br>
<br>


## 1. 제작 기간 & 팀원
### 2021년 9월 13일 ~ 2021년 9월 17일
 >+ 4인 1조 프로젝트
 >+ 임동건-회원가입
 >+ 배나영-메인페이지
 >+ 김세연-마이페이지
 >+ 박재현-로그인
<br>
<br>
<br>



## 2. 데모영상
<img width="80%" src="https://user-images.githubusercontent.com/89460880/133869354-9a9a1a41-f78f-4c8a-9773-9a60b9281467.gif"/>

웹사이트 링크 : http://donggunlim.shop/
<br>
<br>
<br>



## 3. 기술 스택
### Back-end
>+ Python 3
>+ Flask 2.0.1
>+ MongoDB 4.4
>+ Pyjwt 1.7.1
>+ Jinja2 3.0.1
### Front-end
>+ JQuery 3.5.1
>+ Bulma 0.9.2
### deploy
>+ AWS EC2 (Ubuntu 18.04 LTS)
<br>
<br>
<br>



## 4. 핵심기능
#### 로그인, 회원가입
>+ JWT를 이용하여 로그인과 회원가입을 구현하였습니다.
>+ 아이디와 닉네임의 중복확인이 가능합니다.
#### 봉사활동 list 실시간 크롤링
>+ 모집/마감 기한, 봉사시간 등의 데이터를 실시간으로 받아와 리스트 update합니다.
#### 마이페이지
>+ 스크랩한 봉사활동 관리 및 봉사시간을 확인 할 수있습니다.
<br>
<br>
<br>

## 5. 함 해결한 문제  
### 로그아웃 버튼 클릭 시 mytoken을 지우지 못하는 현상($.cookie is not a function)이 나타남 어떡하지?   
- 로그인시 브라우저에 토큰이 저장이 된것은 확인을 해서 제거해주는 함수 오류를 검색후
플러그인(<script type=text/javascriptsrc=https://cdnjs.cloudflare.com/ajax/libs/jquery-cookie/1.4.1/jquery.cookie.min.js></script>) 추가를 했습니다.

### 라이브러리 동시 사용 시 html상 이미지, css 깨짐 현상 발생  
- 원인: Bulma, Bootstrap 라이브러리를 동시에 사용하다 보니  두 기능간 충돌  
- 해결: 기존 mainpage, mypage에 Bulma 모달 창 기능 삭제 후  html, css로  구현

### 봉사활동 카드를 어떤 방식을 배치할 수 있을까?
 - CSS에서 flex속성을 이용해서 카드를 배치했다.
     justify-content: space-between; 속성을 사용했을 때 
     마지막 줄의 봉사활동 카드가 2개일 경우 카드가 양 옆으로 정렬되는 문제는
     ::after를 사용해서 문제를 해결

### 마감일을 현재 날짜에 맞게 보여줄 수 있을까?
 - 서버에서 데이터를 받아올 때 DB에 있던 모집기간의 마지막 날과 현재 날짜를 빼서
     현재 날짜에 맞는 마감일 데이터를 받아올 수 있었다.
      python의 datetime 클래스를 사용했다. 

### 봉사활동 카드를 마감일이 임박한 순서대로 보여줄 수 있을까?
 - 서버에서 데이터를 받아올 때 정렬 함수를 사용해서 마감일 기준으로 데이터를 받아왔다. 
     rows = sorted(rows, key=(lambda x: x['deadline'])) 

### 마이페이지에서 메인페이지로 이동할 경우, 크롤링한 데이터가 중복되서 화면에 나타난다. 원인이 무엇일까?
- 메인페이지에서 마이페이지로 이동할 때 봉사 데이터가 담겨있는 리스트가 초기화되지 않았기 때문에 초기화되지 않은 상태에서 추가로 데이터를 넣었기 때문으로 예상됨
- 리스트에서 중복된 데이터를 제거하여 해결함

### 메인페이지에서 데이터를 보여줄 때 정렬이 안 된다. 원인이 무엇일까?
- 서버쪽에서 데이터를 보내줄 때 정렬이 안 된 상태에서 보내준다는 점을 확인함
- Sorted 함수와 lambda를 이용해서 마감일이 남은 날 기준으로 정렬

### 로그인한 계정마다 좋아요 누른 봉사 정보가 달라야하는데, 어떻게 해야할까?
- 로그인할 때 저장한 토큰에서 아이디값을 가져옴
- 좋아요를 눌렀을 때 봉사 정보가 DB에 들어가는데, 이 과정에서 아이디값도 같이 저장
- DB에서 데이터를 조회할 때 아이디값 기준으로 조회해서 마이페이지에 전달



