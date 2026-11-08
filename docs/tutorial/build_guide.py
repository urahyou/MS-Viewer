"""Build the illustrated Chinese beginner guide from verified app captures and examples."""
from pathlib import Path
from html import escape
import json
import math

from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, Table, TableStyle, Image, Flowable
from reportlab.lib.utils import ImageReader

ROOT=Path(__file__).resolve().parents[2]
TMP=ROOT/'tmp/pdfs/guide'
OUT=ROOT/'output/pdf/MS查看器与MeasurementSet_天文学家视角入门.pdf'
FACTS=json.loads((TMP/'facts.json').read_text())
pdfmetrics.registerFont(TTFont('Body','/Library/Fonts/Arial Unicode.ttf'))
pdfmetrics.registerFont(TTFont('Head','/System/Library/Fonts/STHeiti Medium.ttc'))
pdfmetrics.registerFontFamily('Body',normal='Body',bold='Head',italic='Body',boldItalic='Head')
PAGE_W,PAGE_H=A4
M=42
W=PAGE_W-2*M
NAVY=colors.HexColor('#152c43')
TEAL=colors.HexColor('#008b80')
TEXT=colors.HexColor('#24394e')
GRAY=colors.HexColor('#65788b')
PALE=colors.HexColor('#eef6f5')
GOLD=colors.HexColor('#b47e22')
LIGHT=colors.HexColor('#e4ebf0')
STYLES={
 'body':ParagraphStyle('body',fontName='Body',fontSize=10.7,leading=17.3,textColor=TEXT,wordWrap='CJK',spaceAfter=0),
 'small':ParagraphStyle('small',fontName='Body',fontSize=9.2,leading=14.1,textColor=GRAY,wordWrap='CJK'),
 'table':ParagraphStyle('table',fontName='Body',fontSize=9.8,leading=14.2,textColor=TEXT,wordWrap='CJK'),
 'header':ParagraphStyle('header',fontName='Head',fontSize=10,leading=14.2,textColor=colors.white,wordWrap='CJK'),
 'h2':ParagraphStyle('h2',fontName='Head',fontSize=14,leading=21,textColor=TEAL,wordWrap='CJK'),
 'lead':ParagraphStyle('lead',fontName='Head',fontSize=12.3,leading=20,textColor=NAVY,wordWrap='CJK'),
}

class Vector(Flowable):
    def __init__(self,width,height,fn):
        super().__init__();self.width=width;self.height=height;self.fn=fn
    def draw(self):self.fn(self.canv,self.width,self.height)


def para(s,kind='body'):
    return Paragraph(s,STYLES[kind])

class Guide:
    def __init__(self):
        OUT.parent.mkdir(parents=True,exist_ok=True)
        self.c=canvas.Canvas(str(OUT),pagesize=A4,pageCompression=1)
        self.c.setTitle('读懂 MS：从天文学观测到查看器操作')
        self.c.setAuthor('MS Viewer project')
        self.c.setCreator('MS Viewer tutorial builder')
        self.c.setSubject('中文初学者图解教程，含真实 ALMA 样例、模拟示例与逐步操作')
        self.page_no=0;self.y=0;self.sizes=[]
    def page(self,title,section,subtitle=''):
        self.page_no+=1;self.y=PAGE_H-44
        c=self.c;c.setFillColor(TEAL);c.setFont('Head',9)
        c.drawString(M,self.y,section)
        self.y-=34;c.setFillColor(NAVY);c.setFont('Head',24)
        c.drawString(M,self.y,title)
        self.y-=15
        if subtitle:self.p(subtitle,'small',after=8)
        c.setStrokeColor(LIGHT);c.line(M,self.y-2,PAGE_W-M,self.y-2)
        self.y-=20
        c.bookmarkPage(f'p{self.page_no}')
        c.addOutlineEntry(title,f'p{self.page_no}',0)
    def put(self,flow,after=10):
        width,height=flow.wrap(W,10000)
        if self.y-height<69:
            raise RuntimeError(f'Page {self.page_no} overflow: y={self.y:.1f}, height={height:.1f}, {str(flow)[:100]}')
        flow.drawOn(self.c,M,self.y-height)
        self.y-=height+after
    def p(self,s,kind='body',after=10):self.put(para(s,kind),after)
    def h(self,s):self.p(s,'h2',after=6)
    def table(self,rows,widths=None):
        if widths is None:widths=[W/len(rows[0])]*len(rows[0])
        cells=[[para(str(v),'header' if i==0 else 'table') for v in row] for i,row in enumerate(rows)]
        t=Table(cells,colWidths=widths,hAlign='LEFT')
        t.setStyle(TableStyle([
            ('BACKGROUND',(0,0),(-1,0),NAVY),('VALIGN',(0,0),(-1,-1),'TOP'),
            ('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),
            ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),
            ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.HexColor('#f2f6f8'),colors.white]),
            ('LINEBELOW',(0,0),(-1,0),.5,LIGHT),('LINEBELOW',(0,1),(-1,-1),.35,LIGHT),
        ]));self.put(t,12)
    def box(self,title,body,warning=False):
        bg=colors.HexColor('#fff6e6') if warning else PALE
        t=Table([[para(title,'lead')],[para(body,'body')]],colWidths=[W])
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),bg),('BOX',(0,0),(-1,-1),.4,LIGHT),
           ('LEFTPADDING',(0,0),(-1,-1),12),('RIGHTPADDING',(0,0),(-1,-1),12),
           ('TOPPADDING',(0,0),(-1,0),9),('BOTTOMPADDING',(0,-1),(-1,-1),10),
           ('TOPPADDING',(0,1),(-1,1),2)]));self.put(t,12)
    def image(self,path,max_h=300,caption=None):
        iw,ih=ImageReader(str(path)).getSize();scale=min(W/iw,max_h/ih)
        img=Image(str(path),width=iw*scale,height=ih*scale,hAlign='CENTER')
        # Centre inside a full-width flowable.
        holder=Table([[img]],colWidths=[W]);holder.setStyle(TableStyle([('ALIGN',(0,0),(-1,-1),'CENTER'),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),0)]))
        self.put(holder,7)
        if caption:self.p(caption,'small',after=10)
    def end(self,source=''):
        c=self.c
        if source:
            p=para(source,'small');_,h=p.wrap(W,100)
            p.drawOn(c,M,49-h+10)
        c.setStrokeColor(LIGHT);c.line(M,34,PAGE_W-M,34)
        c.setFont('Body',8);c.setFillColor(GRAY)
        c.drawString(M,22,'MS VIEWER  |  天文学家视角入门  |  2026-11-07')
        c.drawRightString(PAGE_W-M,22,f'{self.page_no:02d} / 21')
        self.sizes.append((self.page_no,round(self.y,1)))
        c.showPage()
    def save(self):
        assert self.page_no==21,self.page_no
        self.c.save();(TMP/'layout-log.json').write_text(json.dumps(self.sizes))


def arrow(c,x1,y1,x2,y2,color=TEAL):
    c.setStrokeColor(color);c.setFillColor(color);c.setLineWidth(1.4);c.line(x1,y1,x2,y2)
    a=math.atan2(y2-y1,x2-x1);l=6
    p=c.beginPath();p.moveTo(x2,y2);p.lineTo(x2-l*math.cos(a-.5),y2-l*math.sin(a-.5));p.lineTo(x2-l*math.cos(a+.5),y2-l*math.sin(a+.5));p.close();c.drawPath(p,fill=1,stroke=0)


def boxdraw(c,x,y,w,h,title,detail='',fill=PALE):
    c.setFillColor(fill);c.setStrokeColor(LIGHT);c.roundRect(x,y,w,h,7,fill=1,stroke=1)
    c.setFillColor(NAVY);c.setFont('Head',12);c.drawCentredString(x+w/2,y+h-21,title)
    if detail:
        c.setFillColor(GRAY);c.setFont('Body',9)
        for i,line in enumerate(detail.split('\n')):c.drawCentredString(x+w/2,y+h-39-i*14,line)


def pipeline(c,w,h):
    xs=[0,132,264,396];labels=[('天空辐射','目标在不同频率\n发出无线电波'),('天线与相关器','天线对共同测量\n复数可见度'),('MS 数据','记录数值与上下文\n本软件在这里检查'),('校准与成像','结合仪器模型\n生成图像或图像立方')]
    for x,(title,detail) in zip(xs,labels):boxdraw(c,x,35,115,92,title,detail)
    for x in xs[:-1]:arrow(c,x+116,81,x+130,81)
    c.setFont('Body',10);c.setFillColor(TEAL);c.drawCentredString(w/2,10,'一条基线的一组数值，要结合许多基线和时刻，才能恢复天空结构。')


def ms_record(c,w,h):
    boxdraw(c,0,182,w,55,'主表的一行：一次带上下文的测量','时刻 + 天线对 + Field + Scan + DDID')
    arrow(c,w/2,182,w/2,162)
    c.setFillColor(NAVY);c.setFont('Head',11);c.drawString(24,148,'这一行的 DATA 单元格：一个小矩阵')
    cw=125;rh=24;x=115;y=98
    c.setFont('Body',10);c.drawCentredString(x+cw/2,126,'XX');c.drawCentredString(x+cw*1.5,126,'YY')
    for r in range(4):
        c.setFillColor(GRAY);c.drawRightString(x-12,y-r*rh+4,f'通道 {r}')
        for col in range(2):
            c.setFillColor(PALE if r%2==0 else colors.HexColor('#f5f8fa'));c.rect(x+cw*col,y-r*rh,cw,rh,fill=1,stroke=0)
            c.setFillColor(TEXT);c.drawCentredString(x+cw*(col+.5),y-r*rh+7,f'{3+r+col} + {4-r}i')
    c.setFillColor(GRAY);c.setFont('Body',8.7);c.drawCentredString(w/2,6,'矩阵中的数值是教学构造；每个格子另有对应的 Flag。')


def time_sequence(c,w,h):
    labels=[('Scan 1','校准源 A\n2 分钟'),('Scan 2','科学目标 B\n10 分钟'),('Scan 3','校准源 A\n2 分钟')]
    for i,(title,detail) in enumerate(labels):boxdraw(c,i*174,30,160,95,title,detail)
    for i in range(2):arrow(c,i*174+161,77,i*174+172,77)
    c.setFont('Body',9);c.setFillColor(GRAY);c.drawString(0,8,'这只是教学安排，不是随附 ALMA 测试集的实际观测计划。')


def ddid_diagram(c,w,h):
    boxdraw(c,0,68,160,85,'DDID 0','第 0 号数据配置')
    boxdraw(c,270,117,240,62,'SPW 1','决定：通道数与各通道频率')
    boxdraw(c,270,22,240,62,'偏振配置 0','决定：XX / XY / YX / YY')
    arrow(c,160,110,265,147);arrow(c,160,110,265,53)
    c.setFillColor(GRAY);c.setFont('Body',9);c.drawString(0,0,'示例来自本项目模拟 MS：DDID 编号与 SPW 编号可以不同。')


def baseline_triangle(c,w,h):
    pts=[(70,50),(250,145),(430,50)]
    for a,b in ((0,1),(0,2),(1,2)):
        c.setStrokeColor(TEAL);c.setLineWidth(2);c.line(*pts[a],*pts[b])
    for i,(x,y) in enumerate(pts):
        c.setFillColor(NAVY);c.circle(x,y,15,fill=1,stroke=0);c.setFillColor(colors.white);c.setFont('Head',11);c.drawCentredString(x,y-4,chr(65+i))
    c.setFillColor(TEXT);c.setFont('Body',10)
    for x,y,s in ((140,113,'基线 AB'),(315,113,'基线 BC'),(240,28,'基线 AC')):c.drawString(x,y,s)
    c.setFont('Body',9);c.setFillColor(GRAY);c.drawString(0,0,'教学示意：3 台天线形成 3 对不同天线的交叉相关基线。')


def overview(c,w,h):
    image=TMP/'sim-ui.png';iw,ih=ImageReader(str(image)).getSize();scale=min(w/iw,h/ih)
    dw,dh=iw*scale,ih*scale;x=(w-dw)/2
    c.drawImage(str(image),x,0,width=dw,height=dh)
    marks=[(.12,.82,'1'),(.10,.89,'2'),(.46,.71,'3'),(.81,.71,'4'),(.62,.34,'5'),(.27,.02,'6')]
    for rx,ry,label in marks:
        px=x+rx*dw;py=ry*dh;c.setFillColor(colors.HexColor('#ffdf88'));c.circle(px,py,10,fill=1,stroke=0)
        c.setFillColor(NAVY);c.setFont('Head',10);c.drawCentredString(px,py-3.5,label)


g=Guide()
# 01
c=g.c;c.setFillColor(NAVY);c.rect(0,0,PAGE_W,PAGE_H,fill=1,stroke=0)
g.page_no=1;c.bookmarkPage('p1');c.addOutlineEntry('读懂 MS：从天文学观测到查看器操作','p1',0)
c.setFillColor(colors.HexColor('#65dbc6'));c.setFont('Head',11);c.drawString(M,PAGE_H-54,'MS VIEWER / 中文图解入门')
c.setFillColor(colors.white);c.setFont('Head',33);c.drawString(M,PAGE_H-116,'先知道自己在看什么')
c.setFont('Head',22);c.drawString(M,PAGE_H-151,'再开始点击 MS 查看器')
p=Paragraph('从天文学家的问题出发，读懂 MeasurementSet、频谱、时间曲线与瀑布图。',ParagraphStyle('cover',fontName='Body',fontSize=13,leading=22,textColor=colors.HexColor('#d0deea'),wordWrap='CJK'))
p.wrap(W,100);p.drawOn(c,M,PAGE_H-221)
c.drawImage(str(TMP/'sim-ui.png'),M,220,width=W,height=W*1120/1600,mask='auto')
c.setFillColor(colors.HexColor('#65dbc6'));c.setFont('Head',15);c.drawString(M,175,'先照做 10 分钟，再回头理解原理')
c.setFillColor(colors.HexColor('#d0deea'));c.setFont('Body',11)
for y,s in ((146,'21 页图解  ·  3 个跟练场景  ·  真实 ALMA 数据与明确标注的模拟数据'),(122,'不要求你先懂复数、干涉测量或 CASA。'),(88,'适用：本项目 MS Viewer 0.1.0，当前中英文界面与只读预览行为。')):c.drawString(M,y,s)
c.setFillColor(colors.HexColor('#93a9bc'));c.setFont('Body',9);c.drawString(M,45,'编写与实测：2026-11-07  |  截图和数值均由本地当前软件生成')
c.showPage();g.sizes.append((1,45))
# 02
g.page('先带着三个问题来读','阅读路线','你不需要一次读完。先完成一个能观察、能描述的小任务。')
g.box('第一问：我选的是哪一份测量？','哪个目标、哪一段观测、哪两台天线、哪个频谱窗、哪个相关乘积？先把上下文说清楚，再解释曲线。')
g.box('第二问：图里究竟画了什么数？','振幅、相位、实部与虚部，是同一个复数测量的不同描述。图中的一个点还可能已经对许多样本做过平均。')
g.box('第三问：这幅图能支持什么结论？','你可以发现值得检查的频率或时刻。是否为天体谱线、干扰或仪器问题，还需要校准信息、其他基线及独立证据。')
g.table([['你的目标','推荐阅读顺序'],['先把软件用起来','第 9 页看界面 → 第 10-11 页做模拟练习 → 第 12-13 页复现你的 ALMA 截图'],['补上最少的原理','第 3-8 页：天空、MS 一行、Field/Scan、SPW/DDID、基线、复数'],['站在天文学家角度检查','第 14-18 页：图形含义、检查顺序、平均、校准与常见疑问'],['自己完成一次记录','第 19 页做练习 → 第 20 页查术语 → 第 21 页查来源']],[100,W-100])
g.p('本教程把“真实样例读数”“人为生成的模拟信号”“便于理解的教学假设”分别标注。不要把教学图中的尖峰，当成真实宇宙发现。','small')
g.end()
# 03
g.page('从天空到 MS：中间发生了什么','01 / 天文学家的起点','射电干涉阵列首先测量天线接收信号之间的关系。')
g.p('假设你想研究一团分子气体：它在哪里？范围多大？某条谱线在什么频率出现？阵列用许多天线对采集信息，之后通过校准与成像来回答这些问题。[S1]')
g.put(Vector(W,165,pipeline),14)
g.h('本软件最适合回答的初步问题')
g.table([['你想检查','在查看器里怎么做'],['哪些数据值得继续分析？','先看目标、频率配置、时间与 Flag；再挑一条基线查看。'],['某个时刻或频率是否特别？','看时间曲线、频谱与瀑布图，记录具体设置和坐标。'],['不同基线或相关乘积是否一致？','只改变一个筛选项，比较变化；同时保留其余设置。']],[150,W-150])
g.box('重要的直觉','可见度反映天空结构在某个空间尺度上的信息，也带有仪器和大气影响。它不是一张已经完成的天体照片。想知道天体在天空中的形状，需要把许多测量结合起来。')
g.end('[S1] ALMA Technical Handbook：干涉测量与可见度。参考链接见第 21 页。')
# 04
g.page('MS 可以先当作“有上下文的测量账本”','02 / 文件里装的是什么','一个 .ms 通常是整个目录，主表与子表需要一起保留。')
g.p('对本教程的干涉测量样例，可以先把主表的一行理解为：某一时刻、某一对天线、某个目标与某种数据配置下的一组测量。行里包含时间和编号；DATA 单元格里装着多个通道与相关乘积的复数。MS 还能保存更复杂的情况及单天线数据。[S2]')
g.put(Vector(W,250,ms_record),12)
g.table([['主表 / 子表','用日常问题理解它'],['MAIN 主表','这一次测了什么数？什么时候测？用哪两台天线？'],['FIELD / ANTENNA','目标编号和天线编号分别对应什么名称与位置？'],['DATA_DESCRIPTION','这个 DDID 对应哪个 SPW 和哪个偏振配置？'],['SPECTRAL_WINDOW / POLARIZATION','各通道的实际频率是什么？记录了哪些相关乘积？']],[170,W-170])
g.box('所以，“1,058 行”不等于 1,058 秒','同一时刻可以有许多天线对、频谱窗和配置，因此主表会有多行。也不能把整个 MS 想成固定形状的三维方块；不同 DDID 的通道数可能不同。')
g.end('[S2] MeasurementSet v2 定义；矩阵示例为教学构造。')
# 05
g.page('Field 选哪里，Scan 选哪一段','03 / 先确定观测上下文','同一个目标可以被重复观测；一次观测安排中也会切换不同目标。')
g.put(Vector(W,140,time_sequence),12)
g.h('两个编号回答不同问题')
g.p('<b>Field（观测目标或指向）</b>回答“看哪里”。它记录的是目标方向等信息；在马赛克观测里，同一天体也可能对应多个指向。<b>Scan（扫描）</b>通常帮助识别一个观测段，实际划分由观测安排决定；编号不必连续，也不能把一个 Scan 理解成固定秒数。[S2][S3]')
g.h('你看到的 ALMA 测试集')
g.table([['界面中的目标','该样例出现的扫描','怎么理解'],['0: J1617-7717','Scan 1','0 是 FIELD_ID；后面是文件记录的名称。'],['1: J1423-7829','Scan 3','这是一项不同的 Field；编号 1 不代表扫描 1。'],['全部目标','当前其他条件下的所有扫描','会把多个 Field 纳入选择；做物理比较时建议先分别查看。']],[174,105,W-279])
g.box('不要仅凭目标名称判断观测用途','“科学目标”“相位校准源”“大气校准”等角色应结合观测意图或日志。本测试集含校准相关意图，不能直接当作某个完整科学项目来解读。',True)
g.end('真实字段与扫描来自本地 ALMA 样例；[S2][S3] 说明数据结构与筛选。')
# 06
g.page('SPW 是频率设置，DDID 是配置入口','04 / 你反复遇到的两个缩写','把 SPW 想成一段接收频率，把通道想成这段频率内的采样格。')
g.p('<b>SPW（Spectral Window，频谱窗）</b>规定频率通道等设置。通道有自己的实际频率，可能升序、降序或不等间距；编号 2 不表示 2 GHz。<b>DDID（Data Description ID）</b>通过一个配置编号，同时指向 SPW 和偏振配置。[S2]')
g.put(Vector(W,185,ddid_diagram),9)
g.h('ALMA 样例中实际出现的配置')
g.table([['界面选项','通道数','本样例的通道中心频率'],['DDID 1 / SPW 1','64','约 84.321555-86.290305 GHz'],['DDID 2 / SPW 2','1','85.290305 GHz；只有一个频率点']],[163,60,W-223])
g.p('这些是通道中心的范围，不等同于精确频谱覆盖边界。完整带宽、通道宽度和有效频率分辨率还要查相应元数据。两项均记录 XX、XY、YX、YY。','small')
g.box('操作上的记忆法','先选 DDID / SPW，确认通道数与实际频率，再选相关乘积。只有一个通道时，频谱只有一个点；用它无法判断一条窄谱线的形状。')
g.end('[S2] DDID → SPW / POLARIZATION；数值为本地 ALMA 样例读数。')
# 07
g.page('一条基线，就是一对天线','05 / 基线与相关乘积','不同天线对提供不同的空间尺度与方向信息。')
g.put(Vector(W,172,baseline_triangle),8)
g.p('界面里的 <b>DA41 → DV14</b> 表示选取 ANTENNA1=DA41、ANTENNA2=DV14 的记录。对不同天线的交叉相关，较长的投影基线通常探测更细的角尺度；这个关系也随波长变化。不能把某条基线的数值当成单台天线的亮度。[S1]')
g.h('XX、XY、YX、YY 是信号组合')
g.table([['相关乘积','直观含义（线偏振接收器示例）'],['XX','第一台天线的 X 接收信号，与第二台的 X 信号做相关。'],['YY','两台天线各自的 Y 接收信号做相关。'],['XY / YX','把两台天线的不同接收分量交叉组合。']],[80,W-80])
g.box('初学时先固定 XX，再一次只改一项','X、Y 是接收器分量标签，不是图的横轴与纵轴。XX 也不自动等于天体的总强度 Stokes I。当前软件不合成 Stokes 参数，也不自动合并反向基线。[S2]')
g.p('三台天线可组成 3 对不同天线的基线。13 台天线理论上可组成 78 对，但测试集不保证每对、每个时刻都有数据。相同天线配对属于自相关。','small')
g.end('[S1] 基线与角尺度；[S2] 相关乘积与接收器信息。')
# 08
g.page('为什么会有振幅、相位、实部和虚部','06 / 用一个箭头理解复数','不用先学完整的复数理论。把一个测量想成“有长度、有角度的箭头”。')
g.image(TMP/'phasor.png',max_h=232)
g.table([['同一个测量 V = 3 + 4i','数值','你在界面里选择'],['水平分量 a','3','实部（Real）'],['竖直分量 b','4','虚部（Imaginary）'],['箭头长度 sqrt(a² + b²)','5','振幅（Amplitude）'],['箭头相对实轴的角度','约 53.1°','相位（Phase）']],[255,70,W-325])
g.p('天文学里，可见度的振幅和相位共同携带天空结构的信息；观测结果还会受到仪器、大气、几何模型等影响。对一个已校准、位于相位中心的理想点源，可用接近实轴的可见度作直觉参照，但真实目标和未充分校准的数据可以更复杂。[S1][S4]')
g.box('虚部为负，不等于“天体亮度为负”','实部和虚部是箭头在两根轴上的投影，可以为负；振幅是长度，非负。相位接近 ±180° 的跳变，也可能只是角度表示跨过了边界。')
g.end('[S1][S4] 可见度与校准；V = 3 + 4i 为教学构造。')
# 09
g.page('先认清窗口的六个区域','07 / 软件导航','此图用于找位置。后面的练习会把关键图放大解释。')
g.put(Vector(W,358,overview),12)
g.table([['编号','区域','先看什么'],['1','左侧数据筛选','目标、DDID、基线、相关乘积、数据列和显示量。'],['2','文件信息 / MS 元数据','确认打开的文件、望远镜、行数与配置。'],['3','左上频谱','不同频率的平均值。'],['4','右上时间曲线','不同时间的平均值。'],['5','下方瀑布图','每个预览行与通道的数值，由颜色表示。'],['6','底部状态','实际读取了多少行和通道？当前 Flag 比例是多少？']],[40,150,W-190])
g.p('顶部“语言 / Language”可切换中英文并记住选择。下拉项变化后自动更新，也可点击“应用筛选”；面板太长时向下滚动。','small')
g.end('截图为当前软件实际运行的模拟样例，目标 0 / DDID 0 / XX / 振幅。')
# 10
g.page('跟练一：先用模拟数据建立直觉','08 / 5 分钟可以完成','目标：亲手选出一条基线，并说清三张图的共同数据来源。')
g.table([['步骤','在软件里操作'],['1','顶部“样例”菜单 → simulated.ms。'],['2','DDID / 频谱窗 → DDID 0 / SPW 1。'],['3','观测目标 → 0: Simulated calibrator；扫描 → 全部扫描。'],['4','基线 → DEMO-01 → DEMO-02；相关乘积 → XX。'],['5','数据列 → DATA；显示量 → 振幅。勾选“隐藏已标记样本”。'],['6','起始通道 0，结束通道 96；时间偏移留空；点击“应用筛选”。']],[52,W-52])
g.h('你应该看到什么')
g.p('底部约显示 <b>48 行 × 96 通道</b>，Flag 比例约 <b>5.6%</b>。频率为 1350-1400 MHz。左上有一个明显的窄带增强，时间曲线有起伏，瀑布图中有明亮竖条和被隐藏的样本。第 11 页把这些图放大。')
g.box('这个尖峰是故意放进去的','生成器在通道 32 加了人为增强，对应约 1366.842105 MHz；还加入了噪声、时间变化和 Flag。它用于练习“找到并描述特征”，不是一个真实天体谱线。',True)
g.h('试着只改变一件事')
g.p('取消“隐藏已标记样本”，看看空白区域是否出现数值；再恢复勾选。随后把显示量改成“相位”。记住：数据选择没变，变的是同一组复数的显示方式。')
g.end('本页所有信号为确定性模拟数据；行数、频率与 Flag 比例已实测。')
# 11
g.page('把三张图当成同一份数据的三个视角','09 / 读图练习','保持第 10 页的筛选不变，先看每张图“平均掉了哪一维”。')
g.image(TMP/'three-plots.png',max_h=410,caption='由同一份模拟数据重绘；空白为隐藏或无有效值的格子。色条与软件一样采用有效值的 2%-98% 范围，超出者显示端点颜色。')
g.table([['图','它概括了什么','这次你能说什么'],['频谱','每个通道对有效预览行求平均。','通道 32 附近有增强。'],['时间曲线','每一行对有效通道求平均。','平均振幅随时间变化。'],['瀑布图','保留每个预览行、每个通道的值。','增强持续在同一通道；部分样本被隐藏。']],[72,213,W-285])
g.p('颜色要结合右侧色条读。黄色表示数值更大，不自动代表“更多数据”“更可靠”或“更热”；显示量改成相位时，颜色代表角度。','small')
g.end('数值来自模拟 MS 的 Field 0 / DDID 0 / DEMO-01→DEMO-02 / XX。')
# 12
g.page('跟练二：复现你的单通道 ALMA 画面','10 / 用真实样例解开疑问','目标：知道“只有一个点”和“一条条横带”究竟从哪里来。')
g.table([['项目','设置'],['文件','样例 → mssel_test_small.ms（ALMA）'],['选择','DDID 2 / SPW 2；全部目标；全部扫描；DA41 → DV14；XX'],['显示','DATA → 虚部；勾选“隐藏已标记样本”；通道范围 [0, 1)']],[90,W-90])
g.image(TMP/'alma1-ui.png',max_h=340,caption='当前软件真实截图。单通道频谱已显示标记点，并在底部明确提示“横向颜色重复”。')
g.box('先认出三个事实','只有 1 个通道，频率为 85290.305000 MHz，即 85.290305 GHz；当前有 23 个预览行；隐藏 Flag 后有 15 行仍有效。单通道没有可供连接的频率序列，所以频谱是一个点。')
g.end('ALMA 测试集不是完整科研交付；本页读数仅针对上述选择。')
# 13
g.page('图为什么会空？先看 Flag 与目标','11 / 真实读数逐项解释','仍使用第 12 页的 DDID 2、DA41→DV14、XX、DATA、虚部。')
g.image(TMP/'alma-single.png',max_h=315,caption='以实际数值重绘。原始 DATA 没有提供 QuantumUnits，因此这里保留“原始单位”，不擅自写 Jy。')
g.table([['观测目标','读取行数','被标记行数','隐藏后有效行'],['全部目标','23','8','15'],['0: J1617-7717','7','7','0'],['1: J1423-7829','16','1','15']],[191,70,87,W-348])
g.p('在这个选择中，按时间排好的前 8 行全部被标记；第一条未标记样本出现在首行之后约 <b>96.192 秒</b>。所以时间曲线前段没有线、瀑布图前段空白，都有具体的数据原因。')
g.p('频谱单点的虚部均值约 <b>2.1284 × 10^-5</b>。它是 15 个有效样本的非加权平均，不是“某一秒的测量”，也不能直接解释为天体总通量。')
g.end('本表的“被标记行”限定于所选单通道与 XX；勿推广为整个 MS 的 Flag 状态。')
# 14
g.page('看到条纹，先提出假设，不急着下结论','12 / 天文学家的读图习惯','下图全是人为构造，只训练“看见什么、下一步查什么”。')
g.image(TMP/'patterns.png',max_h=339,caption='教学图统一使用：横轴为通道，纵轴为按时间排序的样本，颜色越亮表示值越大。')
g.table([['你看见的现象','可提出的假设','下一步怎么查'],['固定通道的竖条','谱线、RFI、通道响应等都可能。','查实际频率、其他基线、偏振和校准结果。'],['短时横条','瞬变干扰、系统变化、源变化等。','查实际时刻、Scan/Field 边界、其他天线对。'],['平滑频率趋势','源本身频谱与带通响应都可能参与。','比较 DATA 与已知校准结果，查带通信息。'],['噪声样起伏','可能与热噪声、低信噪比等有关。','做定量噪声检查，核对权重和积分时间。']],[115,185,W-300])
g.p('“看起来像某种形状”只能产生待检验的解释。当前查看器不计算显著性，也不自动判定 RFI 或发现谱线。','small')
g.end('图为原创模拟示意；[S4][S5] 提供校准与 RFI 检查背景。')
# 15
g.page('天文学家通常按什么顺序检查','13 / 把点击变成一个有目的的检查','每次比较尽量只改变一个条件，并记录当前选择。')
g.box('① 先确认“是不是我想要的那份数据”','打开 MS 元数据：核对望远镜、目标、观测日期、通道数与实际频率。测试集中的日期可能很早；文件下载日期与观测日期是两回事。')
g.box('② 先固定一个目标、一段观测和一条基线','优先用振幅建立整体感觉，再看相位；对科学目标与校准观测分别检查。切换目标后，留意可选 Scan 与基线可能同步变化。')
g.box('③ 查“哪里特别”，再做交叉比较','对异常频率或时刻，记录实际坐标。保持目标与显示量不变，改一条基线；然后再比较 XX/YY。不同投影基线本来就可能测到不同结构，不能要求它们数值完全一致。')
g.box('④ 回到校准与科学问题','带通是否处理？相位参考是否合适？权重是否可用？是否需要重新 Flag、校准、成像或做谱线模型？这些步骤需要相应科研工具与观测信息。')
g.h('一次合格的初步描述')
g.p('“在 Field 1、DDID 1、DA41→DV14、XX、DATA 的振幅图上，我看到了某个频率附近的增强；下一步将核对带通、其他基线及校准后的数据。”这比直接说“这里有谱线”更有信息量。')
g.end('[S3][S4] CASA 数据检查与校准；具体流程应按项目和仪器调整。')
# 16
g.page('平均方式和单位，会改变你读出的意思','14 / 最容易误判的两件事','本软件为了预览做了简化，科学测量时要知道这些边界。')
g.h('振幅平均 ≠ 复数平均后取振幅')
g.table([['教学数据','先取振幅再平均','先平均复数再取振幅'],['V1 = 3 + 4i；V2 = -3 - 4i','(5 + 5) / 2 = 5','两个箭头抵消，结果为 0']],[200,151,W-351])
g.p('当前软件振幅曲线使用左边的方法；相位使用圆周平均，例如 +179° 与 -179° 的平均方向接近 ±180°。零可见度没有定义好的相位，合向量抵消时也会显示为空。科研结论需要选用符合目标的平均方法。')
g.h('当前软件怎样概括一块数据')
g.p('频谱沿预览行求平均，时间曲线沿通道求平均；隐藏 Flag 时只使用未标记的有限值。没有使用 WEIGHT 或 WEIGHT_SPECTRUM。默认最多预览 1024 行、2048 通道，超限会抽样，因此曲线不是全数据的加权统计。色条默认取有效值的 2%-98% 范围，相位固定 ±180°；色条裁切不改变原始数值。')
g.h('把科学计数法翻译成普通数字')
g.table([['界面看到','怎样读'],['60，纵轴标 ×1e-06','60 × 10^-6 = 0.000060，乘以该轴原有的单位。'],['85290.305 MHz','除以 1000，等于 85.290305 GHz。'],['轴上有 Jy','软件读取到相应单位；模拟数据按设计标注 Jy。'],['轴上没有单位','先查元数据或处理记录；不默认把数值当作 Jy。']],[190,W-190])
g.end('平均、抽样与单位处理来自当前实现及实测；CASA 的正式统计/平均设置另见 [S3]。')
# 17
g.page('数据列、校准与成像：各自负责什么','15 / 从预览走向科学分析','一个列名只说明约定用途，不足以证明数据完成了哪些处理。')
g.table([['数据列','常见用途','使用前的核对'],['DATA','保存观测可见度；也可能已被某些处理流程改写。','看来源、HISTORY、处理脚本。'],['CORRECTED_DATA','按惯例保存应用校准后的可见度。','确认用了哪些校准表和步骤。'],['MODEL_DATA','模型天空对应的预测可见度。','确认模型与目标、频率、方向一致。'],['FLOAT_DATA','非复数测量，常见于单天线数据。','按该仪器的数据约定解释。']],[123,203,W-326])
g.p('本教程的两个公开测试 MS 都只有 DATA 列。列下拉框只显示文件中存在的列；它不会替你生成校准结果。某个列不存在，也不自动意味着文件坏了。')
g.h('把软件放在合适的位置')
g.box('它可以帮你做','只读浏览配置、筛选可见度、查看振幅/相位/实部/虚部、比较频率和时间特征、检查 Flag 对画面的影响、导出图像。')
g.box('需要其他工具继续完成','决定新的 Flag 并写回、规范的加权统计、带通/增益/通量校准、Stokes 合成、速度参考系转换、成像与定量谱线分析。可结合 CASA、AOFlagger 等工具。[S3][S4][S5]')
g.p('这里的“只读”指查看器不写回 MS 数据与 Flag。取消“隐藏已标记样本”只改变画法，不会撤销文件中的标记。','small')
g.end('[S2][S3][S4] 数据列约定与处理流程；本地样例的 DATA 单位元数据为空。')
# 18
g.page('遇到这些画面，先这样排查','16 / 不把显示现象直接当成天体现象','先看设置与有效样本，再讨论物理解释。')
g.table([['你看到什么','先做什么'],['频谱只有一个点','检查通道数。单通道只能给出一个频率上的平均值；看时间曲线或换多通道 SPW。'],['瀑布图都是横带','若只选 1 个通道，每行横向是同一个数；先看底部单通道提示。'],['整个目标都空白','核对是否有匹配行，再查 Flag。ALMA 样例的 Field 0 在指定基线/单通道/XX 下全部被标记。'],['时间曲线前面没有线','可能是早期样本被隐藏。也要核对选择范围与实际时间；不要把索引当秒。'],['数值有负号','先确认显示量。实部、虚部和相位都可以为负。'],['相位突然跨过 ±180°','角度可能跨越表示边界；同时检查信噪比、Flag 与校准状态。'],['没有我想要的基线或 Scan','当前 DDID 和 Field 下可能没有那种组合；改变一个条件后检查可选项。'],['有尖峰，是否就是谱线？','记录实际频率，比较其他基线、校准结果和观测背景；仅凭尖峰不能确认。']],[137,W-137])
g.h('最简单的重新打开方式')
g.p('在本机终端进入项目目录后运行：<br/><b>cd /Users/urahyou/Desktop/msviewer</b><br/><b>.venv/bin/python -m msviewer --demo</b><br/>随后在“样例”菜单中选择 ALMA 或 BIMA 文件。')
g.end('排查建议基于本软件行为；信号是否可靠仍需观测与校准信息。')
# 19
g.page('跟练三：独立完成一次观测记录','17 / 用一句话检验自己是否理解','先写设置，再写观察，最后写仍需核对的事情。')
g.h('任务 A：把“空白”解释清楚')
g.p('ALMA 样例，DDID 2、DA41→DV14、XX、DATA、虚部，勾选隐藏 Flag。分别选目标 0 和目标 1。为什么一个完全空白，另一个仍有曲线？<br/><b>核对答案：</b>所选目标 0 有 7 行且全部被标记；目标 1 有 16 行，其中 1 行被标记。')
g.h('任务 B：比较两个频率配置')
g.p('保持目标 1 和同一基线，先看 DDID 2，再改为 DDID 1。频谱由几个点变为几个点？<br/><b>核对答案：</b>从 1 个通道变成 64 个通道；频率由约 85.290305 GHz 的单点变成约 84.321555-86.290305 GHz 的通道中心范围。')
g.h('任务 C：完成下面的检查记录')
g.table([['记录项','请填写'],['文件 / 观测日期','________________________________________'],['Field / Scan / DDID / SPW','________________________________________'],['基线 / 相关乘积 / 数据列','________________________________________'],['显示量 / 单位 / 是否隐藏 Flag','________________________________________'],['预览行数 × 通道数 / Flag 比例','________________________________________'],['发现的现象与实际频率或时间','________________________________________'],['我还需要核对什么','________________________________________']],[194,W-194])
g.box('合格的结束语','“我在这组明确的选择下，看到了这个现象；我知道它用哪些有效样本和平均方式画出，也知道接下来需要什么证据。”不必急着给它一个天体物理名称。')
g.end('答案限定于随附 ALMA 测试集和这里明确的选择。')
# 20
g.page('术语速查：把词翻译成问题','18 / 随时回来看这一页','缩写熟悉之后，界面其实是在不断缩小同一份测量的范围。')
g.table([['术语','一句话理解','在软件里怎么用'],['MS / MeasurementSet','保存数值与观测上下文的一组表。','打开整个 .ms 目录。'],['Visibility / 可见度','通常是干涉天线对测得的复数。','选择要显示哪种复数分量。'],['Field / 观测目标','看哪个方向或指向？','选择一个 Field，避免把不同目标混合。'],['Scan / 扫描','看哪一段观测？','从可选扫描编号中选择。'],['Baseline / 基线','看哪两台天线的组合？','先固定一条不同天线的基线。'],['SPW / 频谱窗','使用哪一组频率通道设置？','核对实际频率和通道数。'],['Channel / 通道','这一小格对应什么频率？','用起始和结束通道选择。'],['DDID / 数据描述编号','哪个 SPW 配哪种偏振配置？','先选 DDID，再看相关乘积。'],['Correlation / 相关乘积','组合哪两路接收信号？','XX、YY、XY、YX 等。'],['Flag / 标记','哪些样本被标成不可用？','决定画图时是否隐藏它们。'],['Amplitude / Phase','箭头的长度 / 角度。','用振幅建立直觉，再看相位。'],['Real / Imaginary','箭头在两根数轴上的分量。','可为负，不能直接当作总亮度。'],['Preview / 预览','有界读取，必要时抽样后的数据。','看底部数量，不把它当全 MS 统计。']],[135,193,W-328])
g.p('通道范围采用 [起始, 结束)：起始包含，结束不包含。例如 [10,20) 读取通道 10-19。时间偏移输入则相对整个 MS 的最早 TIME；右上曲线横轴相对首个预览样本，两者的时间原点可能不同。','small')
g.end('[S2][S3] 提供术语背景；时间原点与范围约定按本软件实现说明。')
# 21
g.page('资料来源与这份教程的边界','19 / 继续学习时从这里出发','下列链接可点击。教程中的软件数值来自本地真实读取，而非对截图的估计。')
refs=[
 ('S1','ALMA Technical Handbook, Cycle 13, §3','干涉测量、可见度、天空亮度与空间尺度。','https://almascience.nrao.edu/documents-and-tools/cycle13/alma-technical-handbook'),
 ('S2','MeasurementSet definition version 2.0, Note 229','MAIN、FIELD、DATA_DESCRIPTION、SPW、偏振与 Flag 的结构定义。','https://casacore.github.io/casacore-notes/229.html'),
 ('S3','CASAdocs: Data Examination/Editing','listobs、plotms、表浏览和数据筛选的官方说明。','https://casadocs.readthedocs.io/en/stable/notebooks/data_examination.html'),
 ('S4','NRAO: Calibration','仪器响应、带通、相位等校准背景。','https://science.nrao.edu/facilities/vla/docs/manuals/obsguide/modes/calibration'),
 ('S5','AOFlagger: Using rfigui','时间-频率图与 RFI 检查工具。','https://aoflagger.readthedocs.io/en/latest/using_rfigui.html'),
 ('S6','casacore 官方测试数据仓库','本地 ALMA、BIMA 测试 MS 的来源；固定提交见项目 sample_catalog.json。','https://github.com/casacore/casacore/tree/a1399b6b99907bd14021920a089403a93c10aba1/ms/MSSel/test'),
]
for code,title,description,url in refs:
    g.p(f'<b>[{code}] {escape(title)}</b><br/>{description}<br/><link href="{escape(url)}" color="#008b80">{escape(url)}</link>','small',after=12)
g.box('范围与版本','本教程针对 MS v2 与本项目查看器当前版本。公开 MS 是上游回归测试切片，历史处理不完整，因此不据此认定它是未校准原始观测、完整科学项目或可发表的测量。模拟信号与教学图均已单独标注。')
g.p('本地核对：三份示例、DDID/SPW 映射、当前软件的平均与 Flag 行为；图与截图制作日期为 2026-11-07。软件不写回 MS 数据与 Flag。更大数据集、其他仪器与不同处理流程，需要重新核对元数据及适用性。','small')
g.end('概念与操作均为原创解释；未复制外部资料的整页图或长段文字。')
g.save()
print(OUT)
print('pages',g.page_no,'size',OUT.stat().st_size)
