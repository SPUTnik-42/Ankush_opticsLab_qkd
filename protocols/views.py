from django.shortcuts import render
from django.http import Http404
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io, base64

from .simulators import bbm92 as bbm92_simulator

def landing_page(request):
    return render(request, 'landing_page.html')

def dashboard(request, protocol_name):
    if protocol_name != 'bbm92':
        raise Http404("Protocol not implemented yet.")
    
    simulator = bbm92_simulator

    if request.method == 'POST':
        # Safely parse numeric input
        def get_float(name, default):
            try: return float(request.POST.get(name, default))
            except: return default

        def get_float_list(name, default_list):
            val = request.POST.get(name, "")
            if not val.strip(): return default_list
            try: return [float(x.strip()) for x in val.split(',')]
            except: return default_list

        # Source
        mu = get_float('mu', 0.1)
        
        # Detector
        alice_det_eff = get_float('alice_det_eff', 0.145)
        bob_det_eff = get_float('bob_det_eff', 0.145)
        alice_dc = get_float('alice_dc_base', 6.02) * (10 ** -6)
        bob_dc = get_float('bob_dc_base', 6.02) * (10 ** -6)
        intrinsic_err = get_float('intrinsic_err', 0.015)

        # Channel
        channel_mode = request.POST.get('channel_mode', 'fiber')
        alice_ch_base_eff = get_float('alice_ch_base_eff', 1.0)
        bob_ch_base_eff = get_float('bob_ch_base_eff', 1.0)
        
        # Fiber
        fiber_att_list = get_float_list('fiber_att_list', [0.18, 0.21, 0.24])

        # FSO
        atmos_vis_list = get_float_list('atmos_vis_list', [40, 30, 20, 10, 5])
        beam_waist = get_float('beam_waist', 0.01)
        receiver_diam = get_float('receiver_diam', 0.3)
        weather = request.POST.getlist('weather')
        if not weather:
            weather = ["very clear", "clear", "partly clear", "hazy", "foggy"]

        # Plot Settings
        max_distance = get_float('max_distance', 350)
        position_of_source = request.POST.get('position_of_source', 'middle')

        # Protocol
        bandwidth = get_float('bw_base', 2.0) * (10 ** 11)
        rep_rate = get_float('rep_base', 2.49) * (10 ** 8)
        pmd = get_float('pmd_base', 5.0) * (10 ** -13)
        f_corr = get_float('f_corr', 1.22)
        is_decoherence = request.POST.get('decoherence') == 'yes'

        kwargs = {
            'alice_detector_efficiency': alice_det_eff,
            'bob_detector_efficiency': bob_det_eff,
            'alice_channel_base_efficiency': alice_ch_base_eff,
            'bob_channel_base_efficiency': bob_ch_base_eff,
            'alice_dark_count_rate': alice_dc,
            'bob_dark_count_rate': bob_dc,
            'intrinsic_detector_error_rate': intrinsic_err,
            'beam_waist': beam_waist,
            'receiver_diameter': receiver_diam,
            'bandwidth': bandwidth,
            'repetition_rate': rep_rate,
            'pmd_coefficient': pmd,
            'bidirection_error_correction_efficiency': f_corr,
            'is_decoherence': is_decoherence
        }

        import numpy as np

        # Clear plots to avoid overlap
        plt.clf()
        simulator.plot_qber_vs_distance(
            mu=mu, 
            distance_values=np.linspace(0, max_distance, 150),
            position_of_source=position_of_source,
            fiber_attenuation_list=fiber_att_list,
            channel_mode=channel_mode,
            weather_list=weather,
            atmos_visibility_list=atmos_vis_list,
            save_fig=False,
            **kwargs
        )
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches="tight")
        buf.seek(0)
        qber_plot = base64.b64encode(buf.read()).decode('utf-8')
        plt.close()
        
        plt.clf()
        simulator.plot_skr_vs_distance(
            mu=mu, 
            distance_values=np.linspace(0, max_distance, 150),
            position_of_source=position_of_source,
            fiber_attenuation_list=fiber_att_list,
            channel_mode=channel_mode,
            weather_list=weather,
            atmos_visibility_list=atmos_vis_list,
            save_fig=False, 
            log_scale=True,
            **kwargs
        )
                                      
        buf2 = io.BytesIO()
        plt.savefig(buf2, format='png', bbox_inches="tight")
        buf2.seek(0)
        skr_plot = base64.b64encode(buf2.read()).decode('utf-8')
        plt.close()

        context = {
            'qber_plot': qber_plot,
            'skr_plot': skr_plot,
            'simulated': True,
            'protocol_name': protocol_name,
            'summary': {
                'mu': mu,
                'max_distance': max_distance,
                'channel_mode': channel_mode.upper(),
                'alice_det_eff': alice_det_eff,
                'bob_det_eff': bob_det_eff,
                'rep_rate': rep_rate,
                'bandwidth': bandwidth
            }
        }
    else:
        context = {'simulated': False, 'protocol_name': protocol_name}
        
    try:
        return render(request, f'{protocol_name}.html', context)
    except Exception:
        return render(request, 'bbm92.html', context)
