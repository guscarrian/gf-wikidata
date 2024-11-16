import json
import urllib.request
from urllib.parse import parse_qs
from urllib.request import Request
from daison import *
import sys
import pgf
import datetime
import time
from email import utils

def autorize(code, start_response):
  import os
  path = os.path.dirname(os.path.abspath(__file__))
  with open(path+"/SECRET") as f:
	  secret = f.read().strip()
  req = Request("https://github.com/login/oauth/access_token?client_id=3b54eb78b27f94e182d0&client_secret="+secret+"&code="+code,
                headers={"Accept": "application/json"})
  with urllib.request.urlopen(req) as response:
    res=json.loads(response.read())
    token=res["access_token"]
  req = Request("https://api.github.com/user",
                headers={"UserAgent": "GF Wikidata",
                         "Authorization": "token "+token})
  with urllib.request.urlopen(req) as response:
    res=json.loads(response.read())
    user = res["login"]
    name = res.get("name")  # if name is missing or if we get "null" value from GitHub
    if not name:
        name = user
    email = res.get("email")  # if email is missing or if we get "null" value from GitHub
    if not email:
        email = user+"@github.com"
    author = name+" <"+email+">"
  path="/wikidata/index.wsgi"
  start_response('302 REDIRECT',
                 [('Location',path)
                 ,('Set-Cookie', 'user='+user)
                 ,('Set-Cookie', 'author='+author)
                 ,('Set-Cookie', 'token='+token)
                 ])
  yield b''

def prelude(qid,lang,edit):
  yield b'<html>'
  yield b' <title>GFpedia</title>'
  yield b' <head>'
  yield b'     <link rel="stylesheet" type="text/css" href="../wordnet/gf-wordnet.css">'
  yield b'     <link rel="stylesheet" type="text/css" href="gf-wikidata.css">'
  yield b' </head>'
  if edit:
    yield b' <body onload="init_editor()">'
  else:
    yield b' <body>'
  yield b'     <div class="gp-head">'
  yield b'        <div id="p-personal">'
  yield b'           <a id="logIn" href="https://github.com/login/oauth/authorize?scope=user:email%20public_repo&client_id=3b54eb78b27f94e182d0">Log In</a>'
  yield b'&nbsp;&nbsp;'
  yield b'           <a id="commit" href="javascript:gfwordnet.commit(this)" style="display: none">Commit</a>'
  yield b'        </div>'

  yield b'        <div id="right-navigation">'
  if qid:
    yield b'<ul class="gp-navigation">'
    if edit:
        yield b'<li><a href="index.wsgi?id='+bytes(qid,"utf-8")+b'&lang='+bytes(lang,"utf-8")+b'">Page</a></li><li class="selected">Edit</li>'
    else:
        yield b'<li class="selected">Page</li><li><a href="index.wsgi?id='+bytes(qid,"utf-8")+b'&lang='+bytes(lang,"utf-8")+b'&edit=1">Edit</a></li>'  
    yield b'</ul>'

  yield b'          <form class="search-box">'
  yield b'             <input class="search-box-input" type="search" name="search"'
  yield b'                    placeholder="Search GFpedia" aria-label="Search GFpedia"'
  yield b'                    autocapitalize="sentences" title="Search GFpedia" id="searchInput"'
  yield b'                    autocomplete="off"'
  yield b'                    oninput="showSearches(this)"'
  yield b'                    onkeypress="searchInputOnKeyPress(event)"'
  yield b'                    onkeydown="searchInputOnKeyDown(event)">'
  yield b'             <img class="search-box-button" src="search.svg">'
  yield b'             <table class="search-box-results" id="searchResults"></table>'
  yield b'         </form>'
  yield b'       </div>'
  yield b'     </div>'
  yield b'     <div class="gp-panel">'
  yield b'         <img class="gp-logo" src="gp-logo.svg">'
  yield b'         <div class="gp-panel-section">'
  yield b'           <table>'

  if qid:
    yield b'             <tr><td><a href="https://cloud.grammaticalframework.org/wikidata/index.wsgi">Main page</a></td></tr>'
    yield b'             <tr><td><a href="https://www.wikidata.org/wiki/'+bytes(qid,"utf8")+b'">Wikidata item</a></td></tr>'

  yield b'           </table>'
  yield b'         </div>'

langs = {
  "af": ("Afrikaans", "ParseAfr"),
  "ar": ("Arabic",    "ParseAra"),
  "bg": ("Bulgarian", "ParseBul"),
  "ca": ("Catalan",   "ParseCat"),
  "zh": ("Chinese",   "ParseChi"),
  "nl": ("Dutch",     "ParseDut"),
  "en": ("English",   "ParseEng"),
  "et": ("Estonian",  "ParseEst"),
  "fi": ("Finnish",   "ParseFin"),
  "fr": ("French",    "ParseFre"),
  "de": ("German",    "ParseGer"),
  "it": ("Italian",   "ParseIta"),
  "ko": ("Korean",    "ParseKor"),
  "mt": ("Maltese",   "ParseMlt"),
  "pl": ("Polish",    "ParsePol"),
  "pt": ("Portuguese","ParsePor"),
  "ro": ("Romanian",  "ParseRon"),
  "ru": ("Russian",   "ParseRus"),
  "sl": ("Slovenian", "ParseSlv"),
  "so": ("Somali",    "ParseSom"),
  "es": ("Spanish",   "ParseSpa"),
  "sw": ("Swahili",   "ParseSwa"),
  "sv": ("Swedish",   "ParseSwe"),
  "th": ("Thai",      "ParseTha"),
  "tr": ("Turkish",   "ParseTur"),
  "zu": ("Zulu",      "ParseZul")
  }

home = [
  b'<h1 class="gp-page-title">GF Pedia</h1>',
  b'<p>This is an experiment to see to what extend we can generate encyclopedic articles ',
  b'based on information from <a href="https://www.wikidata.org/">Wikidata</a> and by using ',
  b'the resource grammars in <a href="http://www.grammaticalframework.org/">GF</a> plus ',
  b'lexical resources in <a href="https://cloud.grammaticalframework.org/wordnet/">GF WordNet</a>.</p>'
  b'<p>Search for a Wikidata entity in the upper left corner.</p>'
  ]

epilogue = [
  b'     </div>',
  b'     <script src="/js/support.js"></script>',
  b'     <script src="https://unpkg.com/vis-network@9.0.4/standalone/umd/vis-network.min.js"></script>',
  b'     <script src="../wordnet/js/gf-wordnet.js"></script>',
  b'     <script src="../wordnet/js/wordcloud2.js"></script>',
  b'     <script src="../wordnet/js/cookies.js"></script>',
  b'     <script src="gf-wikidata.js"></script>',
  b' </body>',
  b'</html>'
  ]

def render_page(query, start_response):
    start_response('200 OK', [('Content-Type','text/html; charset=utf-8')
                             ,('Date', utils.formatdate(time.mktime(datetime.datetime.now().timetuple())))
                             ])

    qid   = query.get("id",[None])[0]
    if qid != None and (qid[0] != "Q" or not qid[1:].isdigit()):
        qid = None

    lang  = query.get("lang",["en"])[0]
    if lang not in langs:
        lang="en"

    edit = query.get("edit",["0"])[0]=="1"

    for line in prelude(qid,lang,edit):
        yield line

    yield b'         <div class="gp-panel-section">'
    yield b'           <h3 class="gp-page-title">Languages</h3>'
    yield b'           <table id="from">'
    for code,(name,cnc) in langs.items():
        yield b'             <tr>'
        if code != lang:
            if qid != None:
                if edit:
                    yield bytes('<td><a href="index.wsgi?id='+qid+'&lang='+code+'&edit=1">'+name+'</a></td>','utf8')
                else:
                    yield bytes('<td><a href="index.wsgi?id='+qid+'&lang='+code+'">'+name+'</a></td>','utf8')
            else:
                yield bytes('<td><a href="index.wsgi?lang='+code+'">'+name+'</a></td>','utf8')
        else:
            yield bytes('<td><b>'+name+'</b></td>','utf8')
        if edit:
            yield bytes('<td><input type="checkbox" name="'+cnc+'" onchange="select_language()"></td>','utf8')
        yield b'</tr>'
    yield b'         </table>'
    yield b'       </div>'
    yield b'     </div>'
    yield b'     <div class="gp-body" id="content" data-lang="'+bytes(lang,"utf8")+b'">'

    import wordnet
    from nlg import render, render_list
    from nlg.util import get_entity, ConcrHelper

    wordnet.w.__pgf__.checkoutBranch()

    if qid != None:
        entity = get_entity(qid)
        cnc = ConcrHelper(wordnet.grammar.languages[langs[lang][1]],lang,edit)

        lex_fun = cnc.get_lex_fun(qid,link=False)
        if not lex_fun:
            lex_fun = cnc.get_person_name(entity)
            if lex_fun:
                cnc.removeLink(lex_fun)

        if lex_fun:
            for s in render(cnc,lex_fun,entity):
                yield bytes(s,"utf8")
        elif qid == "Q11750":
            for s in render_list(cnc,qid):
                yield bytes(s,"utf8")
        else:
            yield bytes('<h1 class="gp-page-title">'+qid+"</h1>","utf8")
            yield bytes("<p>There is no NLG for this item yet.</p>","utf8")

        if cnc.exprs:
            yield b'<div class="gp-dump">'
            for e in cnc.exprs:
                yield bytes("<p>"+str(e)+"</p>","utf8")
            yield b"</div>"
    else:
        for line in home:
            yield line

    for line in epilogue:
        yield line

def application(env, start_response):
    query = parse_qs(env["QUERY_STRING"])

    code  = query.get("code",[None])[0]
    if code != None:
        return autorize(code, start_response)
    else:
        return render_page(query, start_response)

if __name__ == "__main__":
    import os
    def start_response(*args):
        pass
    for line in application(os.environ, start_response):
        print(line.decode("utf-8"))
