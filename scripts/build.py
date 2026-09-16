import pandas as pd, json, os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data'))
# Periodo del panel: se cuentan las vistas OCURRIDAS en estos anios, sin
# importar cuando se publico el video.
ANIOS=('2024','2025','2026')
# Ventana del export metricas_video.csv. Ese archivo trae totales acumulados
# por video, sin columna de fecha, asi que no se puede recortar por codigo:
# hay que re-exportarlo desde YouTube Studio con el rango deseado y actualizar
# esta constante. Mientras no coincida con ANIOS, el panel lo avisa.
VENTANA_VIDEOS=('2023','2026')
m=pd.read_csv('metricas_canal.csv'); c=pd.read_csv('catalogo_videos.csv'); v=pd.read_csv('metricas_video.csv')
m=m[m.mes.str[:4].isin(ANIOS)].copy()
m['subs_netos']=m.subs_ganados-m.subs_perdidos
def agg(g):
    s=g[['vistas','impresiones','clicks','subs_ganados','subs_perdidos','subs_netos','ingresos_usd','tiempo_repr_horas']].sum(min_count=1)
    s['ctr']=s.clicks/s.impresiones*100
    s['rpm']=s.ingresos_usd/(s.vistas/1000)
    s['avd']=(g.avd_seg*g.vistas).sum()/g.vistas.sum()
    s['dias']=len(g); s['ing_nulos']=int(g.ingresos_usd.isna().sum())
    s['parcial']=bool(g.mes_parcial.any())
    return s
mon=m.groupby('mes').apply(agg)
out={'periodo':list(ANIOS)}
def row(k):
    r=mon.loc[k]; return {x:float(r[x]) for x in ['vistas','impresiones','ctr','subs_netos','subs_ganados','subs_perdidos','ingresos_usd','rpm']}
out['resumen']={'actual':row('2026-08'),'prev':row('2026-07'),'yoy':row('2025-08'),'dias':int(mon.loc['2026-08','dias'])}
# weekly
wk=m.groupby('semana').apply(lambda g: pd.Series({'vistas':g.vistas.sum(),'imp':g.impresiones.sum(),'clicks':g.clicks.sum(),'parcial':bool(g.semana_parcial.any()),'inicio':g.semana_inicio.iloc[0],'dias':len(g)}))
out['semanas_parciales']=wk[wk.parcial].index.tolist()
full=wk[~wk.parcial].sort_index()
last=full.tail(52)
out['semanal']=[{'sem':i,'inicio':r.inicio,'vistas':int(r.vistas),'ctr':r.clicks/r.imp*100} for i,r in last.iterrows()]
# check contiguity
out['sem_excluidas_en_rango']=[s for s in out['semanas_parciales'] if s>=last.index[0]]
# monthly
mm=mon[mon.index>=ANIOS[0]+'-01']
out['meses_parciales']=mm[mm.parcial].index.tolist()
mm=mm[~mm.parcial]
out['mensual']=[{'mes':i,'vistas':int(r.vistas),'subs':int(r.subs_netos),'rpm':float(r.rpm),'imp':int(r.impresiones),'ctr':float(r.ctr),'ing':float(r.ingresos_usd)} for i,r in mm.iterrows()]
# videos
d=c.merge(v,on='video_id',how='inner')
out['periodo_videos']=list(VENTANA_VIDEOS)
out['n_total']=len(d); out['n_cortos']=int((~d.es_largo).sum())
out['n_nuevos']=int((d.es_largo&(d.dias_publicado<14)).sum())
f=d[d.es_largo&(d.dias_publicado>=14)].copy()
out['n_filtrado']=len(f)
cats=[]
for k,g in f.groupby('categoria'):
    V=g.vistas.sum()
    cats.append({'cat':k,'n':len(g),'vpv':V/len(g),'ctr':g.clicks.sum()/g.impresiones.sum()*100,
      'pct':(g.pct_reproducido*g.vistas).sum()/V,'avd':(g.avd_seg*g.vistas).sum()/V,'subs1k':g.subs_ganados.sum()/V*1000,'vistas':V,'imp':g.impresiones.sum()})
cats.sort(key=lambda x:-x['ctr']); out['categorias']=cats
f['ctr']=f.clicks/f.impresiones*100
cols=['video_id','titulo','categoria','fecha_publicacion','vistas','impresiones','ctr','pct_reproducido','subs_ganados']
s=f.sort_values('ctr',ascending=False)
out['top']=s.head(15)[cols].to_dict('records'); out['bottom']=s.tail(15).sort_values('ctr')[cols].to_dict('records')
out['min_imp_top']=float(s.head(15).impresiones.min()); out['min_imp_bot']=float(s.tail(15).impresiones.min())
out['corte']=m.fecha.max()
json.dump(out,open('data.json','w'),default=float)
print(json.dumps({k:out[k] for k in ['resumen','semanas_parciales','sem_excluidas_en_rango','meses_parciales','n_total','n_cortos','n_nuevos','n_filtrado','min_imp_top','min_imp_bot']},indent=1,default=float))
print(out['semanal'][0],out['semanal'][-1],len(out['semanal']))
for x in cats: print(x)
print(pd.DataFrame(out['top'])[['titulo','impresiones','ctr']].to_string()); print(pd.DataFrame(out['bottom'])[['titulo','impresiones','ctr']].to_string())
print(mon[['vistas','subs_netos','rpm','ing_nulos']].tail(4))
mm2=m.dropna(subset=['rpm_usd','ingresos_usd']).copy()
mm2['calc']=mm2.ingresos_usd/mm2.vistas*1000
dd=mm2[(mm2.calc-mm2.rpm_usd).abs()>0.05]
out['rpm_dif_dias']=len(dd)
out['rpm_dif_ago']=[{'fecha':r.fecha,'yt':float(r.rpm_usd),'calc':float(r.calc)} for r in dd[dd.mes=='2026-08'].itertuples()]
out['rpm_nulos']=m[m.rpm_usd.isna()].fecha.tolist(); out['ing_nulos']=m[m.ingresos_usd.isna()].fecha.tolist()
json.dump(out,open('data.json','w'),default=float)
