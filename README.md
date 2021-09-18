# 항해99 3기 15조
나만의 봉사 활동 page를 관리하고 싶지 않으신가요? 저희 사이트는 인천 연수구 가치 봉사 사이트는 현재 모집중인 봉사활동 리스트와 상세페이지를 제공합니다. Mypage에서 관심있는 봉사활동을 스크랩하고 완료 시간도 체크해 보세요!



## 1. 제작 기간 & 팀원
### 2021년 6월 13일 ~ 2021년 6월 17일
 >+ 4인 1조 프로젝트
 >+ 임동건-회웝가입
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

## 5. 함꼐 해결한 문제  
>+ 로그아웃 버튼 클릭 시 mytoken을 지우지 못하는 현상($.cookie is not a function)이 나타나서 플러그인(<script type=text/javascript
            src=https://cdnjs.cloudflare.com/ajax/libs/jquery-cookie/1.4.1/jquery.cookie.min.js></script>) 추가를 했습니다.

>+ 라이브러리 동시 사용 시 html상 이미지, css 깨짐 현상 발생  
원인: Bulma, Bootstrap 라이브러리를 동시에 사용하다 보니  두 기능간 충돌
해결: 기존 mainpage, mypage에 Bulma 모달 창 기능 삭제 후  html, css로  구현            


