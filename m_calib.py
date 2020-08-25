# ------------------------------------------------------------------
# spectral line calibration for determination of distortion parameters
# ------------------------------------------------------------------
import logging
import os.path as path
import time
from pathlib import Path

import numpy as np

import PySimpleGUI as sg
import m_calfun85 as lfun
import m_specfun as m_fun
import myselect as sel


def main():
    # -------------------------------------------------------------------------
    # default parameters of fit, use for Watec
    # read in from default ini-file, see m_specfun
    # -------------------------------------------------------------------------
    sg.SetGlobalIcon('Koji.ico')
    sg_ver = sg.version.split(' ')[0]
    print('PySimpleGUI', sg_ver)
    if int(sg_ver.split('.')[0]) >= 4 and int(sg_ver.split('.')[1]) >= 9:
        sg.change_look_and_feel('SystemDefault')  # suppresses message in PySimpleGUI >= 4.9.0
    version = '0.8.6'
    pngdir = '_tmp_/cal_'
    # start with default ini_file
    ini_file = 'm_set.ini'
    par_text, par_dict, res_dict, fits_dict, opt_dict = m_fun.read_configuration(ini_file,
                                            m_fun.par_dict, m_fun.res_dict, m_fun.opt_dict)
    fits_dict['VERSION'] = version
    if par_text == '':
        sg.PopupError(f'no valid configuration found, default {ini_file} created')
        m_fun.write_configuration(ini_file, par_dict, res_dict, fits_dict, opt_dict)
    # [lam0, scalxy, fitxy, imx, imy, f0, pix, grat, rotdeg, binning, comment,
    #  infile, outfil,linelist,typesqrt] = list(par_dict.values())
    outfil = par_dict['s_outfil']
    parkey = list(par_dict.keys())
    # [zoom, wsx, wsy, wlocx, wlocy, xoff_calc, yoff_calc, xoff_setup, yoff_setup,
    #     debug, fit_report, win2ima, opt_comment, pngdir, png_name, outpath, mdist, colorflag, bob_doubler,
    #     plot_w, plot_h, i_min, i_max, graph_size, show_images] = list(opt_dict.values())
    wsize = (opt_dict['win_width'], opt_dict['win_height'])
    wloc = (opt_dict['win_x'], opt_dict['win_y'])
    debug = opt_dict['debug']
    notok, linelist, lines = lfun.get_linelist(par_dict['s_linelist'], par_dict['f_lam0'])
    if linelist:
        par_dict['s_linelist'] = linelist
    infile = par_dict['s_infile']
    # for new draw_scaled_image
    graph_size = opt_dict['graph_size']
    graph_s2 = (graph_size, graph_size)
    idg = None
    imbw = []


# ------------------------------------------------------------------------------
#   Start Menu Definition   
# ------------------------------------------------------------------------------
    menu_def = [
                ['File', ['Save Actual File', 'Exit']],
                # ['Tools', ['Offset', ['Special', 'Normal', ], 'Undo'], ],
                ['Tools', ['Offset', 'Edit Text File', 'Edit Log File'], ],
                ['Help', 'About...'], ]

    # elements of main window, which are updated:
    image_elem = sg.Graph(canvas_size=graph_s2, graph_bottom_left=(0, 0), graph_top_right=graph_s2, key='image')

    log_elem = sg.Multiline('Log', size=(38, 12), autoscroll=True)
    filename_display_elem = sg.Text(infile, size=(100, 1), key='image_filename')

    # layout main window
    layout_parameters = sg.Frame('', [[sg.Frame('Setup',
                  [[sg.Input(ini_file, size=(40, 1), key='setup_file')],
                   [sg.Button('Load Setup'), sg.Button('Edit Setup')]])],
               [sg.Frame('Video Extraction',
                  [[sg.Input('', size=(40, 1), key='avi_file')],
                   [sg.Button('Load Avi'), sg.Text('Calibration image:'), sg.Button('Save Image')],
                   [sg.Input('', size=(40, 1), key='image_file')]])],
               [sg.Frame('Select Lines',
                  [[sg.Input(infile, size=(40, 1), key='input_file')],
                   [sg.Button('Load Image'), sg.Text('Calibration data, ".txt":')],
                   [sg.Input(outfil, size=(40, 1), key='output_file',
                             tooltip='select file for calibration data')],
                   [sg.Button('Select File'), sg.Button('Edit File'),
                    sg.Button('Select Lines')],
                   [sg.Text('Linelist'), sg.Input(linelist, size=(20, 1), key='linelist'),
                    sg.Button('Load L_list')]])],
               [sg.Frame('Calibration',
                  [[sg.Button('LSQF'), sg.Checkbox('SQRT-Fit',
                                    default=par_dict['b_sqrt'], key='SQRT-Fit'),
                    sg.Checkbox('Fit-xy', default=par_dict['b_fitxy'], key='fitxy')]])],
                   [sg.Text('Results:')], [log_elem]])

    layout_image = [[sg.Menu(menu_def, tearoff=True)],
             [layout_parameters, sg.Column([[filename_display_elem], [image_elem]])]]

# ------------------------------------------------------------------------------
#   Initialize Window
# ------------------------------------------------------------------------------
    winsetup_active = False
    contr = 1
    logtext = 'Logfile ' + time.strftime("%Y%m%d_%H%M%S") + '\n'
    info = f'M_CALIB version {version}, lfun version {lfun.version}, m_fun.version {m_fun.version}'
    logtext += info + '\n'
    logging.info(info)
    current_dir = path.abspath('')
    window_title = f'M_CALIB, Version: {version}, {current_dir} , Image: '
    winmain = sg.Window(window_title, layout_image, location=wloc,
                        size=wsize, resizable=True)
    winmain.read(timeout=0)
    image_data, idg, actual_file = m_fun.draw_scaled_image('tmp.png', image_elem, opt_dict, idg)


# ------------------------------------------------------------------------------
#   Loop main window
# ------------------------------------------------------------------------------
    while True:
        ev1, values = winmain.Read(timeout=100)

        if ev1 in (None, 'Exit'):
            if winsetup_active:
                winsetup.Close()
                del winsetup
            winmain.Close()
            del winmain
            if ev1 == 'Exit':
                m_fun.write_configuration('m_set.ini', par_dict, res_dict, fits_dict, opt_dict)
                logging.info('m_set.ini saved, M_CALIB FINISHED')
                logtext += 'm_set.ini saved\nM_CALIB FINISHED'
                with open('Log' + time.strftime("%Y%m%d_%H%M%S") + '.txt', 'w') as f:
                    f.write(logtext)
            break

        # adjust image size, update image if necessary
        if wsize != winmain.Size:
            wsize = winmain.Size
            opt_dict['win_width'] = wsize[0]
            opt_dict['win_height'] = wsize[1]
            # print('new widow size', wsize)
            image_data, idg, actual_file = m_fun.draw_scaled_image(actual_file, image_elem,
                                                                   opt_dict, idg, tmp_image=True)
        winmain.set_title(window_title + str(actual_file))
        log_elem.Update(logtext)

# -------------------------------------------------------------------------------
#       Video
# -------------------------------------------------------------------------------
        if ev1 is 'Load Avi':
            avifile, info = m_fun.my_get_file(winmain['avi_file'].Get(), title='Get Video File',
                                    file_types=(('Video Files', '*.avi'), ('ALL Files', '*.*')),
                                    default_extension='.avi')
            logtext += info + '\n'
            if avifile:
                logging.info(f'start video conversion: {str(avifile)}')
                logtext += 'start video conversion: WAIT!\n'
                winmain['avi_file'].Update(avifile)
                winmain.refresh()
                nim, dattim, sta, out = m_fun.extract_video_images(avifile, pngdir, bobdoubler=False,
                                                    binning=par_dict['i_binning'], bff=False, maxim=20)
                logging.info(f'finished video conversion: {str(avifile)}')
                logging.info(f'nim: {str(nim)} date time: {dattim} station: {sta}')
                logtext += ('finished video conversion: ' + avifile + '\n' +
                            f'nim: {str(nim)} date time: {dattim} ' + '\n' +
                            f'station: {sta}' + '\n')
                print('nim:', nim, dattim, sta)
                imbw = m_fun.create_background_image(pngdir, nim)
                # save average image as png and fit
                lfun.save_fit_png('avi.png', imbw)
                # TODO: use function from m_fun or move save_fit_png
                image_data, idg, actual_file = m_fun.draw_scaled_image('avi.fit', image_elem, opt_dict, idg)

        if ev1 in ('Save Image', 'Save Actual File'):
            imfilename, info = m_fun.my_get_file(winmain['image_file'].Get(), title='Save image',
                                    file_types=(('Image Files', '*.fit'), ('ALL Files', '*.*')),
                                    save_as=True, default_extension='*.fit',)
            if imfilename:
                imfilename = m_fun.change_extension(imfilename, '')
                try:
                    lfun.save_fit_png(imfilename, imbw)
                    logtext += info + '\n'
                    winmain['image_file'].Update(imfilename)
                    winmain['image_filename'].Update(imfilename)
                except:
                    sg.PopupError('no video converted or image saved')
            else:
                'no image saved, missing filename'

# -------------------------------------------------------------------------------
#       Load, save image
# -------------------------------------------------------------------------------
        if ev1 == 'Load Image':
            files, info = m_fun.my_get_file(winmain['input_file'].Get(), title='Load image',
                                file_types=(('Image Files', '*.fit'), ('PNG-File', '*.png'),
                                ('BMP-File', '*.bmp'), ('ALL Files', '*.*')),
                                default_extension='*.fit', multiple_files=True)
            nim = len(files)
            new_infile = ''
            if nim == 0:
                sg.Popup('No file selected, keep last image')
                # imbw, opt_dict = lfun.load_image('tmp.png', opt_dict)
                image_data, idg, actual_file, imbw = m_fun.draw_scaled_image('tmp.png', image_elem,
                                                                    opt_dict, idg, get_image=True)
            else:
                # imbw, opt_dict = lfun.load_image(files[0], opt_dict)  # with extension
                image_data, idg, actual_file, imbw = m_fun.draw_scaled_image(files[0], image_elem, opt_dict,
                                                                        idg, tmp_image=True, get_image=True)
                infile = m_fun.m_join(files[0])
                if nim == 1:
                    if len(imbw):
                        if not files[0].lower().endswith('.fit'):  # further processing is with fits-images
                            error = m_fun.write_fits_image(imbw, m_fun.change_extension(infile, '.fit'),
                                                           fits_dict, dist=False)
                            if error:
                                infile = ''
                            else:
                                logging.info(f'Load_Image: {infile} size: {str(imbw.shape)}')
                                logtext += 'Load_Image: ' + infile + ' size: ' + str(imbw.shape) + '\n'
                        new_infile = m_fun.change_extension(infile, '')
                    else:
                        sg.PopupError(' File not found or not read')
                        # imbw, opt_dict = lfun.load_image('tmp.png', opt_dict)
                elif nim > 1:
                    error = False
                    shape0 = imbw.shape
                    for file in files:
                        # imbw, tmp_dict = lfun.load_image(file, opt_dict, imagesave=False)
                        # load images to compare shape
                        # TODO: shorter version of load array only, no need to draw image
                        image_data, idg, actual_file, imbw = m_fun.draw_scaled_image(file, image_elem,
                                                                            opt_dict, idg, get_image=True)

                        if imbw.shape != shape0:
                            sg.PopupError('all files must have the same format, try again!', keep_on_top=True)
                            error = True
                            break
                    if not error:
                        for f in range(nim):
                            files[f] = path.relpath(files[f])
                            # im, opt_dict = lfun.load_image(files[f], opt_dict, imagesave=False)
                            # TODO: shorter version of load array only, no need to draw image
                            image_data, idg, actual_file, im = m_fun.draw_scaled_image(files[f], image_elem,
                                                                            opt_dict, idg, get_image=True)
                            if f == 0:
                                imbw = im
                            else:
                                imbw = np.maximum(imbw, im)
                        new_infile = infile + '_peak_' + str(nim)
                        lfun.save_fit_png(new_infile, imbw)
                        image_data, idg, actual_file = m_fun.draw_scaled_image(m_fun.change_extension(new_infile,
                                                            '.fit'), image_elem, opt_dict, idg, tmp_image=True)
                        logging.info(f'image saved as: {new_infile} (.fit, .png)')
                        logtext += 'Load_Images:' + '\n'
                        for f in range(nim):
                            logtext += files[f] + '\n'
                        logtext += f'image saved as: {new_infile}, .png)\n'
            if new_infile:
                infile = m_fun.m_join(new_infile)
                winmain['image_filename'].Update(infile)
                par_dict['s_infile'] = infile
                (imy, imx) = imbw.shape[:2]
                par_dict['i_imx'] = imx
                par_dict['i_imy'] = imy
            winmain['input_file'].Update(new_infile)

# -------------------------------------------------------------------------------
#       Select Lines        
# ------------------------------------------------------------------------------
        if ev1 == 'Select File':
            old_outfil = winmain['output_file'].Get()
            outfil, info = m_fun.my_get_file(old_outfil,
                               title='Load measured calibration lines file',
                               file_types=(('Calibration Files', '*.txt'), ('ALL Files', '*.*')),
                               save_as=False, default_extension='*.txt')
            if not outfil:
                outfil = old_outfil
                if not outfil:
                    sg.PopupError('no File selected, try again')
            if outfil:
                outfil = m_fun.change_extension(outfil, '')
                outfil = m_fun.m_join(outfil)
                winmain['output_file'].Update(outfil)

        if ev1 == 'Load L_list':
            linelist, info = m_fun.my_get_file(winmain['linelist'].Get(),
                               title='Get Linelist',
                               file_types=(('Linelist', '*.txt'), ('ALL Files', '*.*')),
                               default_extension='*.txt')
            if not linelist or linelist[:-1] == 'l':
                linelist = 'l'
            linelist = m_fun.change_extension(linelist, '')
            winmain['linelist'].Update(linelist)
            par_dict['s_linelist'] = linelist

        if ev1 == 'Select Lines':
            infile = winmain['input_file'].Get()
            outfil = winmain['output_file'].Get()
            if infile:
                if not Path(infile + '.fit').exists():
                    imbw, opt_dict = lfun.load_image(infile, opt_dict)
                # 'tmp.png' created with tmp_image=True, needed for sel.select_lines
                image_data, idg, actual_file = m_fun.draw_scaled_image(m_fun.change_extension(infile, '.fit'),
                                                    image_elem, opt_dict, idg, tmp_image=True, get_image=False)
                p = Path(m_fun.change_extension(outfil, '.txt'))
                if not Path(p).exists():
                    if not p.parent.exists():
                        Path.mkdir(p.parent, exist_ok=True)
                        # p = path.relpath(Path.joinpath(p.parent, p.name).with_suffix('.txt'))
                        p = m_fun.m_join(Path.joinpath(p.parent, p.name), '.txt')
                    outfil = str(Path(p).with_suffix(''))
                    par_dict['s_outfil'] = outfil
                notok, linelist, lines = lfun.get_linelist(par_dict['s_linelist'], par_dict['f_lam0'])
                winmain.Disable()
                sel.select_lines(infile, contr, lines, res_dict, fits_dict, wloc, outfil)
                winmain.Enable()
                winmain.BringToFront()
                logging.info(f'Finished, saved {outfil}.txt')
                logtext += ('Finished, saved ' + outfil + '.txt\n')
            else:
                sg.PopupError('no image selected, try again')

# ------------------------------------------------------------------------------
#       LSQ-Fit        
# ------------------------------------------------------------------------------
        if ev1 == 'LSQF':
            outfil = winmain['output_file'].Get()
            if Path(m_fun.change_extension(outfil, '.txt')).exists():
                winmain['output_file'].update(outfil)
                par_dict['s_outfil'] = outfil
                par_dict['b_sqrt'] = winmain['SQRT-Fit'].Get()
                par_dict['b_fitxy'] = winmain['fitxy'].Get()
                parv = list(par_dict.values())
                logging.info(f'outfil: {outfil} START LSQF')
                logtext += 'outfil: ' + outfil + '\n'
                logtext += 'START LSQF ...\n'
                winmain.refresh()
                try:
                    par, result = lfun.lsqf(parv, debug=debug, fit_report=opt_dict['fit-report'])
                    (scalxy, x00, y00, rotdeg, disp0, a3, a5, errorx, errory) = par
                    image_data, idg, actual_file = m_fun.draw_scaled_image(outfil+'_lsfit.png', image_elem,
                                                                           opt_dict, idg)
                    rot = rotdeg*np.pi/180
                    resv = np.float32([scalxy, x00, y00, rot, disp0, a3, a5])
                    reskey = ['scalxy', 'x00', 'y00', 'rot', 'disp0', 'a3', 'a5']
                    reszip = zip(reskey, resv)
                    res_dict = dict(list(reszip))
                    # write default configuration as actual configuration
                    m_fun.write_configuration('m_cal.ini', par_dict, res_dict, fits_dict, opt_dict)
                    logging.info('Result LSQF:')
                    logging.info(result)  # more detailed info
                    logtext += 'Result LSQF saved as m_cal.ini:\n'
                    logtext += result
                    print('END OF LSQ-Fit!!!')
                    logtext += 'END OF LSQ-Fit!\n'
                except:
                    sg.PopupError(f'Error in LSQ-fit, wrong {outfil} ?')
                    result = ' Error with: ' + str(outfil) + '.txt'
                    logging.info(result)
                    result += '\n----------------------------------------\n'
                    logtext += result
            else:
                sg.PopupError('no such file: ' + outfil + '.txt')

# ------------------------------------------------------------------------------
#       Setup            
# ------------------------------------------------------------------------------
        if ev1 in ('Load Setup', 'Edit Setup') and not winsetup_active:
            print(ev1)
            if ev1 == 'Load Setup':
                ini_file, info = m_fun.my_get_file(winmain['setup_file'].Get(),
                                     title='Get Configuration File',
                                     file_types=(('Configuration Files', '*.ini'), ('ALL Files', '*.*')),
                                     default_extension='*.ini')
                par_text, par_dict, res_dict, fits_dict, opt_dict = m_fun.read_configuration(ini_file,
                                                        m_fun.par_dict, m_fun.res_dict, m_fun.opt_dict)
                fits_dict['VERSION'] = version
                if par_text == '':
                    sg.PopupError(f'no valid configuration found, use current configuration',
                                  keep_on_top=True)
            else:  # edit conf, update values from main menu
                par_dict['s_infile'] = winmain['input_file'].Get()
                par_dict['s_outfil'] = winmain['output_file'].Get()
                par_dict['s_linelist'] = winmain['linelist'].Get()
                par_dict['b_sqrt'] = winmain['SQRT-Fit'].Get()
                par_dict['b_fitxy'] = winmain['fitxy'].Get()
            parv = list(par_dict.values())
            winsetup_active = True
            winmain.Disable()
            wloc_setup = (wloc[0] + opt_dict['setup_off_x'], wloc[1] + opt_dict['setup_off_y'])
            # update values of setup window
            input_row = []
            input_elem = []
            debug = opt_dict['debug']
            # if debug: print('setup parv:', parv)
            for k in range(15):
                input_elem.append(sg.Input(parv[k], size=(30, 1)))
                input_row.append([sg.Text(parkey[k], size=(10, 1)), input_elem[k]])
            filename_ini_in_elem = sg.InputText(ini_file, size=(34, 1))
            # layout of setup window
            zoom_elem = sg.Input(str(opt_dict['zoom']), key='zoom', size=(7, 1))
            headings = ['Parameter', 'Value']
            header = [[sg.Text(h, size=(7, 1)) for h in headings]]
            input_rows = [[sg.Text('Zoom', size=(5, 1)), zoom_elem]]
            ind = 9  # current index of next list element
            checkbox = [[sg.Checkbox('debug', default=opt_dict['debug'], pad=(10, 0), key='debug')],
                        [sg.Checkbox('fit-report', default=opt_dict['fit-report'], pad=(10, 0), key='fit-report')],
                        [sg.Checkbox('scale_win2ima', default=opt_dict['scale_win2ima'], pad=(10, 0),
                                     key='scale_win2ima')]]
            ind += 3
            layout_options = sg.Frame('Options',
                                header + input_rows + checkbox + [[sg.Text('Comment', size=(10, 1))],
                                [sg.InputText(opt_dict['comment'], size=(16, 1), key='comment')]])

            # Parameters
            layout_setup = [[sg.Frame('Settings',
                            [[sg.Frame('Lasercal',
                            [[sg.Text('Lasercal')],
                            # [[sg.Text(ki[k], size=(5,1)), sg.Input(kval[k])] for k in range(15)],
                            input_row[0], input_row[1], input_row[2], input_row[3],
                            input_row[4], input_row[5], input_row[6], input_row[7],
                            input_row[8], input_row[9], input_row[10], input_row[11],
                            input_row[12], input_row[13], input_row[14],
                            # [input_row[k] for k in range(15)], does not work
                            [filename_ini_in_elem],
                            [sg.Button('SaveC', size=(6, 1)),
                            sg.Button('Apply', size=(6, 1)), sg.Button('Cancel', size=(6, 1))]]),
                            layout_options]])]]

            winsetup = sg.Window('Parameters', layout_setup, disable_close=True,
                disable_minimize=True, location=wloc_setup, keep_on_top=True,
                no_titlebar=False, resizable=True)

        while winsetup_active:
            evsetup, valset = winsetup.Read(timeout=100)
            if evsetup is 'Cancel':
                winsetup_active = False
                winmain.Enable()
                winsetup.Close()

            if evsetup in ('Apply', 'SaveC'):
                for k in range(15):
                    key = parkey[k]
                    if key[0] == 'b':
                        if valset[k] == '0': 
                            par_dict[key] = False
                        else:
                            par_dict[key] = True
                    elif key[0] == 'i':
                        par_dict[key] = int(valset[k])
                    elif key[0] == 'f':
                        par_dict[key] = float(valset[k])
                    else:
                        par_dict[key] = valset[k]
                    input_elem[k].Update(valset[k])
                infile = par_dict['s_infile']
                if infile:
                    # imbw, opt_dict = lfun.load_image(infile, opt_dict)
                    image_data, idg, actual_file, imbw = m_fun.draw_scaled_image(m_fun.change_extension(infile, '.fit'),
                                                            image_elem, opt_dict, idg, tmp_image=True, get_image=True)
                    if not image_data:
                        imbw = []
                else:
                    imbw = []
                if len(imbw):
                    par_dict['s_infile'] = str(infile)
                    winmain['input_file'].Update(infile)
                    winmain['image_filename'].Update(infile)
                else:
                    sg.PopupError(f'Image {infile} not found, load tmp.png instead:', keep_on_top=True)
                    # imbw, opt_dict = lfun.load_image('tmp.png', opt_dict)
                    image_data, idg, actual_file, imbw = m_fun.draw_scaled_image('tmp.png', image_elem, opt_dict,
                                                                                    idg, get_image=True)
                winmain['setup_file'].Update(ini_file)
                winmain['output_file'].Update(par_dict['s_outfil'])
                winmain['SQRT-Fit'].Update(par_dict['b_sqrt'])
                winmain['fitxy'].Update(par_dict['b_fitxy'])
                # parv = list(par_dict.values())
                wloc = winmain.current_location()
                (x, y) = winsetup.current_location()
                opt_dict['setup_off_x'] = x - wloc[0]
                opt_dict['setup_off_y'] = y - wloc[1]
                opt_dict['zoom'] = float(valset['zoom'])
                opt_dict['debug'] = valset['debug']
                opt_dict['fit-report'] = valset['fit-report']
                opt_dict['scale_win2ima'] = valset['scale_win2ima']
                opt_dict['comment'] = valset['comment']
                notok = True
                while notok:
                    notok, linelist, lines = lfun.get_linelist(par_dict['s_linelist'], par_dict['f_lam0'])
                    if notok:
                        linelist, info = m_fun.my_get_file(winmain['linelist'].Get(),
                                                     title='Get Linelist',
                                                     file_types=(('Linelist', '*.txt'), ('ALL Files', '*.*')),
                                                     default_extension='*.txt')
                        if not linelist:
                            linelist = 'l'
                            notok = False
                par_dict['s_linelist'] = str(Path(linelist).with_suffix(''))
                winmain['linelist'].Update(par_dict['s_linelist'])
                # parv[13] = par_dict['s_linelist']
                # input_elem[13].Update(parv[13])

                if evsetup in 'SaveC':
                    winsetup.Hide()
                    ini_file, info = m_fun.my_get_file(filename_ini_in_elem.Get(),
                             title='Save Configuration File', save_as=True,
                             file_types=(('Configuration Files', '*.ini'), ('ALL Files', '*.*')),
                             default_extension='*.ini', error_message='no configuration saved: ')
                    if ini_file:
                        m_fun.write_configuration(ini_file, par_dict, res_dict, fits_dict, opt_dict)
                    else:
                        sg.Popup('No file saved', keep_on_top=True)
                logtext += info + '\n'
                winsetup_active = False
                winmain.Enable()
                winsetup.Close()
                    
# ------------------------------------------------------------------------------
        if ev1 == 'Edit Log File':
            m_fun.edit_text_window(m_fun.logfile, select=False, size=(90, 30))

# ------------------------------------------------------------------------------
        if ev1 == 'About...':
            # sg.Popup('Calibration of meteor spectra with grating\n' +
            #     'mounted perpendicular to optical axis\n' +
            #     'see:\nhttps://meteorspectroscopy.org/welcome/documents/\n\n' +
            #     'Martin Dubs, 2019', title='About')
            m_fun.about(version, program='M_Calib')
                        
# ------------------------------------------------------------------------------
        if ev1 == 'Offset':
            if infile:
                if Path(m_fun.change_extension(infile, '.fit')).exists():
                    # imbw, opt_dict = lfun.load_image(infile, opt_dict)
                    image_data, idg, actual_file, imbw = m_fun.draw_scaled_image(m_fun.change_extension(infile, '.fit'),
                                                                            image_elem, opt_dict, idg, get_image=True)
                    print('orig', np.min(imbw), np.max(imbw), np.average(imbw))
                    im = imbw - np.average(imbw)
                    im_std = np.std(im)
                    im_clip = np.clip(im, -2.0*im_std, 2.0*im_std)
                    offset = - np.average(imbw) - np.average(im_clip)
                    print('off', np.min(imbw), np.max(imbw), np.average(imbw))
                    imbw = np.clip(imbw + offset, 0.0, 1.0)
                    file_offset = m_fun.change_extension(infile, '_off.fit')
                    print('clip', np.min(imbw), np.max(imbw), np.average(imbw))
                    m_fun.write_fits_image(imbw, file_offset, fits_dict)
                    # imbw, opt_dict = lfun.load_image(file_offset, opt_dict)
                    # image_elem.update('tmp.png')
                    image_data, idg, actual_file = m_fun.draw_scaled_image(m_fun.change_extension(infile, '_off.fit'),
                                                                           image_elem, opt_dict, idg, tmp_image=True)
                    infile = infile + '_off'
                    winmain['image_filename'].Update(infile)
                    winmain['input_file'].Update(infile)
                    logging.info(f'image with offset saved as: {file_offset}')
                    logtext += f'image with offset saved as: {file_offset}\n'
                    winmain.refresh()
                else:
                    sg.PopupError('file not found, load valid fits image')
        if ev1 in ('Edit Text File', 'Edit File'):
            outfil = winmain['output_file'].Get()
            m_fun.edit_text_window(outfil, size=(50, 30))

    return par_dict


main()
