"""Original teaching figures and numerical plots; all sky-pattern examples are labelled simulated."""
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np

OUT=Path('tmp/pdfs/guide')
font_manager.fontManager.addfont('/System/Library/Fonts/STHeiti Medium.ttc')
plt.rcParams.update({'font.family':'Heiti TC','font.size':10,'axes.titlesize':11,
                     'axes.spines.top':False,'axes.spines.right':False,
                     'axes.labelcolor':'#23384d','text.color':'#23384d',
                     'xtick.color':'#526779','ytick.color':'#526779',
                     'axes.edgecolor':'#c1cdd8','savefig.facecolor':'white'})
D=np.load(OUT/'examples.npz')
TEAL='#008c82'; BLUE='#3563a4'; GOLD='#bb8424'

def save(fig,name):
    fig.savefig(OUT/name,dpi=190,bbox_inches='tight',pad_inches=.13)
    plt.close(fig)

# The same data cube shown three ways, matching the simulated exercise.
fig=plt.figure(figsize=(8.4,7.0),layout='constrained')
gs=fig.add_gridspec(2,2,height_ratios=[1,1.5])
a=fig.add_subplot(gs[0,0]); a.plot(D['sim_frequency_mhz'],D['sim_spectrum'],color=TEAL)
a.set(xlabel='频率（MHz）',ylabel='平均振幅（Jy）',title='① 频谱：沿时间方向平均')
a.annotate('人为加入的窄带增强',xy=(D['sim_frequency_mhz'][32],D['sim_spectrum'][32]),
           xytext=(1354,5.8),arrowprops={'arrowstyle':'->','color':GOLD},fontsize=9,color=GOLD)
a=fig.add_subplot(gs[0,1]);a.plot(D['sim_elapsed_seconds'],D['sim_time_trace'],color=GOLD)
a.set(xlabel='相对首个预览样本的时间（秒）',ylabel='平均振幅（Jy）',title='② 时间曲线：沿频率方向平均')
a=fig.add_subplot(gs[1,:]);values=D['sim_image'];lo,hi=np.percentile(values[np.isfinite(values)],[2,98]);im=a.imshow(values,origin='lower',aspect='auto',cmap='viridis',vmin=lo,vmax=hi)
a.set(xlabel='预览通道索引（0-95）',ylabel='预览行索引（0-47）',title='③ 瀑布图：保留每一行、每一个通道')
fig.colorbar(im,ax=a,label='振幅（Jy）',shrink=.9)
save(fig,'three-plots.png')

# Single-channel example, retaining flags and using actual physical x for spectrum/time.
fig=plt.figure(figsize=(8.4,5.5),layout='constrained')
gs=fig.add_gridspec(2,2,height_ratios=[1,1.2])
a=fig.add_subplot(gs[0,0]);x=D['alma1_frequency_mhz'];y=D['alma1_spectrum']*1e6
a.plot(x,y,'o',color=TEAL,ms=7);a.set_xlim(x[0]-.15,x[0]+.15)
a.ticklabel_format(useOffset=False,axis='x');a.set_xticks([x[0]-.1,x[0],x[0]+.1]);a.set_xticklabels([f'{v:.3f}' for v in (x[0]-.1,x[0],x[0]+.1)]);a.set(xlabel='频率（MHz）',ylabel='虚部（原始单位 × 10^-6）',title='频谱中只有一个均值点')
a.annotate(f'{y[0]:.3f}',(x[0],y[0]),xytext=(0,10),textcoords='offset points',ha='center')
a=fig.add_subplot(gs[0,1]);a.plot(D['alma1_elapsed_seconds'],D['alma1_time_trace']*1e6,color=GOLD,marker='.',ms=4)
a.axvspan(0,D['alma1_elapsed_seconds'][7],alpha=.12,color='#8798a8')
a.set(xlabel='相对首个预览样本的时间（秒）',ylabel='虚部（原始单位 × 10^-6）',title='约 96 秒之后才有未标记样本')
a=fig.add_subplot(gs[1,:]);im=a.imshow(D['alma1_image']*1e6,origin='lower',aspect='auto',cmap='viridis',extent=(0,1,-.5,22.5))
a.axhspan(-.5,7.5,color='#f0f3f6',zorder=-1)
a.set(xlabel='同一个频率通道（横向只是拉宽）',ylabel='预览行索引',title='前 8 行隐藏；其余每行只有一个颜色值')
a.set_xticks([.5],['85.290305 GHz'])
fig.colorbar(im,ax=a,label='虚部（原始单位 × 10^-6）',shrink=.9)
save(fig,'alma-single.png')

# Phasor diagram; constructed values, not any measurement.
fig,ax=plt.subplots(figsize=(6.4,3.8),layout='constrained')
ax.axhline(0,c='#aebac6',lw=.8);ax.axvline(0,c='#aebac6',lw=.8)
ax.annotate('',(3,4),(0,0),arrowprops={'arrowstyle':'->','lw':3,'color':TEAL})
ax.plot([3,3],[0,4],':',color=BLUE);ax.plot([0,3],[4,4],':',color=BLUE)
ax.text(3.15,4.05,'V = 3 + 4i',color=TEAL,fontsize=13)
ax.text(1.1,2.5,'长度 = 振幅 5',rotation=53,color=TEAL)
ax.text(1.25,.35,'角度约 53°',color=GOLD)
ax.set(xlim=(-1,6),ylim=(-.8,5.3),xlabel='实部 a',ylabel='虚部 b',title='教学构造：同一个复数的两种描述')
ax.set_aspect('equal');save(fig,'phasor.png')

# Four ambiguous dynamic-spectrum patterns, generated independently of all telescope data.
rng=np.random.default_rng(42)
base=rng.normal(0,.15,(50,64))
patterns=[]
a=base.copy();a[:,24:26]+=1.3;patterns.append((a,'固定通道增强','竖条：持续出现在同一通道'))
a=base.copy();a[25:28,:]+=1.3;patterns.append((a,'短时宽带增强','横条：许多通道同时变化'))
a=base.copy()+np.linspace(-.4,1,64)[None,:];patterns.append((a,'平滑的频率趋势','渐变：可能含频谱或仪器响应'))
a=base.copy();patterns.append((a,'随机起伏','噪声样外观也需要定量检查'))
fig,axs=plt.subplots(2,2,figsize=(8.4,5.7),layout='constrained')
for ax,(a,title,subtitle) in zip(axs.flat,patterns):
 ax.imshow(a,origin='lower',aspect='auto',cmap='viridis',vmin=-.5,vmax=1.5)
 ax.set(title=title,xlabel='通道索引',ylabel='时间样本索引')
 ax.text(.02,.04,subtitle,transform=ax.transAxes,fontsize=8.5,color='white',bbox={'facecolor':'#132639','alpha':.8,'edgecolor':'none','pad':3})
save(fig,'patterns.png')
print('Figures created')
