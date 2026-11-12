import csv
import io
from fastapi import APIRouter, Request, Depends
from fastapi.responses import Response
from core.auth import context, require, data
from core.security import Problem
from . import models, service
api = APIRouter()

@api.get('/api/state')
async def state(request: Request, ctx=Depends(context)):
    require(ctx, request)
    return models.state(ctx.db, request.query_params)

@api.post('/api/{kind}')
@api.put('/api/{kind}/{id}')
@api.delete('/api/{kind}/{id}')
async def save(request: Request, kind: str, id: int = None, ctx=Depends(context)):
    require(ctx, request, ('Admin',))
    if kind not in ('roads', 'regions', 'jobs'):
        raise Problem('Alamat tidak tersedia.', 404)
    if request.method == 'DELETE':
        service.remove(ctx.db, kind, id)
    else:
        getattr(service, {'roads': 'road', 'regions': 'region', 'jobs': 'job'}[kind])(ctx.db, await data(request), id)
    return {'message': 'Perubahan disimpan.'}

@api.post('/api/roads/{id}/restore')
async def restore(request: Request, id: int, ctx=Depends(context)):
    require(ctx, request, ('Admin',))
    models.find(ctx.db, 'roads', id)
    with ctx.db:
        ctx.db.execute('UPDATE roads SET archived=0 WHERE id=?', (id,))
    return {'message': 'Ruas jalan dipulihkan.'}

@api.get('/api/roads/{id}/inspections')
@api.post('/api/roads/{id}/inspections')
async def inspections(request: Request, id: int, ctx=Depends(context)):
    user = require(ctx, request)
    if request.method == 'GET':
        return models.history(ctx.db, id)
    service.inspect(ctx.db, user, id, await data(request))
    return {'message': 'Hasil inspeksi dicatat.'}

@api.get('/api/jobs/{id}/progress')
@api.post('/api/jobs/{id}/progress')
async def progress(request: Request, id: int, ctx=Depends(context)):
    user = require(ctx, request)
    if request.method == 'GET':
        return models.progress_history(ctx.db, id)
    service.progress(ctx.db, user, id, await data(request))
    return {'message': 'Laporan progres dicatat.'}

@api.post('/api/jobs/{id}/cancellation')
async def cancel(request: Request, id: int, ctx=Depends(context)):
    require(ctx, request, ('Admin',))
    models.find(ctx.db, 'jobs', id)
    values = await data(request)
    if not isinstance(values.get('canceled'), bool):
        raise Problem('Pilihan pembatalan tidak valid.')
    with ctx.db:
        ctx.db.execute('UPDATE jobs SET canceled=? WHERE id=?', (int(values['canceled']), id))
    return {'message': 'Status jadwal diperbarui; riwayat tetap tersimpan.'}

@api.get('/api/export')
async def export(request: Request, ctx=Depends(context)):
    require(ctx, request)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Kode ruas', 'Ruas', 'Wilayah', 'Panjang meter', 'Kondisi inspeksi', 'Tanggal inspeksi', 'Skor prioritas', 'Pekerjaan', 'Mulai', 'Target', 'Progres %', 'Status pekerjaan'])
    rows = models.roads(ctx.db, request.query_params)
    jobs = models.jobs(ctx.db, {r['id'] for r in rows})
    for r in rows:
        for j in [j for j in jobs if j['road_id'] == r['id']] or [{}]:
            fields = [r['code'], r['name'], r['region'], r['length_m'], r['condition'] or 'Belum diinspeksi', r['inspected_on'] or '', r['priority'] if r['priority'] is not None else '', j.get('name', ''), j.get('starts_on', ''), j.get('target_on', ''), j.get('percent', '') if j.get('last_report') else '', j.get('status', '')]
            writer.writerow(["'" + str(v) if str(v).startswith(('=', '+', '-', '@')) else v for v in fields])
    return Response('\ufeff' + output.getvalue(), media_type='text/csv', headers={'Content-Disposition': 'attachment; filename=laporan-pemeliharaan.csv'})
