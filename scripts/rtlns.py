#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

import sys
import json

class RTLNs:
    def __init__(self, socketio, rtl_sdr, logcl):
        self.socketio = socketio
        self.rtl_sdr = rtl_sdr
        self.logcl = logcl
        self.index_namespace = '/'
        self.graph_namespace = '/graph'
        self.app_namespace = '/app'
        self.scan_namespace = '/scan'
        self.routes = (
            self.index_namespace, 
            self.graph_namespace,
            self.scan_namespace,
            self.app_namespace
        )

    def get_routes(self):
        return self.routes

    def add_namespace(self, ns, methods):
        for method in methods:
             self.socketio.on(method, namespace=self.routes[ns])(getattr(self, method))

    def get_dev_status(self):
        if not self.rtl_sdr.dev_open:
            if(self.rtl_sdr.init_device(init_dev=False, show_log=False)):
                self.socketio.emit('dev_status', 1, namespace=self.index_namespace)
            else:
                self.socketio.emit('dev_status', 0, namespace=self.index_namespace)
        else:
            self.socketio.emit('dev_status', 1, namespace=self.index_namespace)

    def disconnect_request(self):
        if self.rtl_sdr.dev_open:
            self.rtl_sdr.close(True)
        self.logcl.log("Stopping server...")
        self.socketio.stop()

    def connect(self):
        self.socket_log("RTLion started.")

    def start_sdr(self, freq=None):
        if not self.rtl_sdr.dev_open:
            if(self.rtl_sdr.init_device()):
                self.socket_log("RTL-SDR device opened. [#" + str(self.rtl_sdr.dev_id) + "]")
                self.create_fft_graph(freq)
            else:
                self.socket_log("Failed to open RTL-SDR device. [#" + str(self.rtl_sdr.dev_id) + "]")
                self.socketio.emit('dev_status', 0, namespace=self.graph_namespace)
        else:
            self.create_fft_graph(freq)

    def stop_sdr(self):
        try:
            self.logcl.log("Stop reading samples from RTL-SDR.")
            self.socket_log("Stop reading samples from RTL-SDR.")
            self.socketio.emit('dev_status', 0, namespace=self.graph_namespace)
            self.c_read = False
            self.n_read = 0
        except Exception as e:
            self.logcl.log("Failed to stop RTL-SDR device.\n" + str(e), 'error')
            sys.exit()

    def restart_sdr(self, new_freq):
        try:
            self.c_read = False
            self.n_read = 0
            self.rtl_sdr.close()
            self.rtl_sdr.center_freq = int(new_freq)
            self.rtl_sdr.init_device(show_log=False)
            self.socketio.emit('new_freq_set', namespace=self.graph_namespace)
        except Exception as e:
            self.logcl.log("Failed to set new frequency.\n" + str(e), 'error')
            sys.exit()

    def start_scan(self, freq, sensivity):
        self.rtl_sdr.sensivity = sensivity
        self.rtl_sdr.close()
        self.rtl_sdr.center_freq = int(freq)
        self.start_sdr(freq=-1)

    def send_cli_args(self, status=0):
        self.socketio.emit(
                'cli_args', 
                {'args': self.rtl_sdr.args, 'status': status}, 
                namespace=self.graph_namespace)

    def update_settings(self, args):
        try:
            self.rtl_sdr.set_args(args)
            self.send_cli_args(status=1)
            self.logcl.log("Settings/arguments updated.")
            self.socket_log("Settings/arguments updated.")
        except:
            self.logcl.log("Failed to update settings.", 'error')

    def server_ping(self): 
        self.socketio.emit('server_pong', namespace=self.graph_namespace)

    def create_fft_graph(self, freq_change):
        self.n_read = self.rtl_sdr.num_read
        self.interval = int(self.rtl_sdr.interval) / 1000.0
        if freq_change == None:
            self.socketio.emit('dev_status', 1, namespace=self.graph_namespace)
            self.socket_log("Creating FFT graph from samples...")
            self.logcl.log("Creating FFT graph from samples...")
            self.logcl.log("Getting graph data with interval " + 
            str(self.interval) + " (" + str(self.n_read) + "x)")
        if freq_change != None and int(freq_change) == -1:
            self.socketio.emit('dev_status', 1, namespace=self.graph_namespace)
            self.socketio.start_background_task(self.send_data_thread)
        else:
            self.c_read = True
            self.socketio.start_background_task(self.rtlsdr_thread)

    def rtlsdr_thread(self):
        while self.c_read:
            fft_data = self.rtl_sdr.get_fft_data()
            self.socketio.emit(
            'fft_data', 
            {'data': fft_data},
            namespace=self.graph_namespace)
            self.socketio.sleep(self.interval)
            self.n_read-=1
            if self.n_read == 0: break
    
    def send_data_thread(self, ns=1, parse_json=False):
        graph_values = self.rtl_sdr.get_fft_data(scan=True)
        try:
            if not parse_json:
                self.socketio.emit(
                    'graph_data', 
                    {'fft': graph_values[0], 
                    'freqs': graph_values[1][0],
                    'dbs': graph_values[1][1]},
                    namespace=self.routes[ns])
            else:
                def get_str_from_list(lst):
                    try: 
                        return ' '.join(str(float(i)) for i in lst)
                    except: 
                        return None
                self.socketio.emit(
                    'graph_data', 
                    graph_values[0] + "|" + \
                    get_str_from_list(graph_values[1][0]) + "|" + \
                    get_str_from_list(graph_values[1][1]),
                    namespace=self.routes[ns])
        except:
            self.socketio.emit(
                    'graph_data', 
                    None,
                    namespace=self.routes[ns])

    def socket_log(self, msg):
        self.socketio.emit('log_message', {'msg': msg}, 
            namespace=self.graph_namespace)