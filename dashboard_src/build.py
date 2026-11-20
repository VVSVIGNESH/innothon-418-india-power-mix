
t=open("index.src.html").read()
lab=open("lab.js").read().replace("if(typeof module!=='undefined')module.exports=Lab;","")
ui=open("lab_ui.js").read()
t=t.replace("<script>\nconst SRC=","<script>"+lab+"</script>\n<script>\nconst SRC=",1)
t=t.replace("</script>\n</body>","</script>\n<script>"+ui+"</script>\n</body>",1)
open("index.html","w").write(t)
