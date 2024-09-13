
import streamlit as st
import time


def get_value_for(default_val, other_info=dict()):
    label = other_info["label"] if "label" in other_info.keys() else " "
    label_vis = other_info["label_vis"] if "label_vis" in other_info.keys() \
                else ("visible" if label != " " else "collapsed")
    _help = other_info["help"] if "help" in other_info.keys() else None
    out_val = "empty val"
    if type(default_val) in [int, float]:
        step = 1 if type(default_val) is int else 0.1
        maximum = other_info["max"] if "max" in other_info.keys() else None
        minimum = other_info["min"] if "min" in other_info.keys() else None
        input_type = other_info["type"] if "type" in other_info.keys() else "number_input"

        if input_type.lower() == "number_input":
            out_val = st.number_input(value=default_val, step=step, min_value=minimum, max_value=maximum, label=label,
                                                  label_visibility=label_vis, help=_help)
        elif input_type.lower() == "slider":
            out_val = st.slider(value=default_val, step=step, min_value=minimum, max_value=maximum, label=label,
                                            label_visibility=label_vis, help=_help)

    elif type(default_val) is str:

        is_password = "password" if ("password" in other_info.keys()) and (other_info["password"] == True) else "default"
        input_type = other_info["type"] if "type" in other_info.keys() else "text_input"

        if input_type.lower() in ["text_input", "text input", "textinput"]:
            out_val = st.text_input(value=default_val, label=label, label_visibility=label_vis, type=is_password, help=_help)
        elif input_type.lower() in ["text_area", "text area", "textarea"]:
            out_val = st.text_area(value=default_val, label=label, label_visibility=label_vis, help=_help)

    elif type(default_val) is bool:
        input_type = other_info["type"] if "type" in other_info.keys() else "toggle"

        if input_type.lower() == "toggle":
            out_val = st.toggle(value=default_val, label=label, label_visibility=label_vis, help=_help)
        elif input_type.lower() in ["checkbox", "check box", "check_box"]:
            out_val = st.checkbox(value=default_val, label=label, label_visibility=label_vis, help=_help)

    return out_val

def generate_inputs_and_return_values(iterable, infos=list()):
    output_item = iterable.copy()
    if type(iterable) not in [list, dict, set]:
        #input_field = st.empty()
        info = {
                "label": "TEST - " + str(type(iterable)),
                "help": "default value is : " + str(iterable)
                }
        output_item = get_value_for(iterable,
                                 other_info=info)

    else:
        if type(iterable) in [list, set]:
            for index, item in enumerate(iterable):
                #input_field = st.empty()
                info = infos[index] if index < len(infos) else dict()
                output_item[index] = get_value_for(item,
                                         other_info=info)

        elif type(iterable) is dict:
            if len(infos) == 0 and "info" in iterable.keys():
                infos = iterable["info"]

            items = iterable["item"]
            for index, item in enumerate(items):
                #input_field = st.empty()
                info = infos[index] if index < len(infos) else dict()
                output_item[item] = get_value_for(iterable[item],
                                         other_info=info)

    return output_item



input_arr = []
if "input_items" in st.session_state.keys():
    input_arr = st.session_state["input_items"]
else:
    input_arr = ["abc", 123, 2.0, True, False, True, "ege.the.engineer", "BULUT", 100.8, 20]
    st.session_state["input_items"] = input_arr

infos = [
    {
        "label": "String input - textarea",
        "help": "default value is 'abc'.",
        "type": "textarea"
    },
    {
        "label": "Number input - int",
        "help": "default value is 123.",
    },
    {
        "label": "Number input - float",
        "help": "default value is 2.0.",
    },
    {
        "label": "Boolean input - checkbox",
        "help": "default value is True",
        "type": "checkbox"
    },
    {
        "label": "Boolean input - Toggle",
        "help": "default value is False",
        "type": "toggle"
    },
    {
    },
    {
        "label": "String input - default",
        "help": "default value is 'ege.the.engineer'.",
    },
    {
        "label": "String input - password",
        "help": "default value is '*****'",
        "password": True
    },
    {
        "type": "slider",
        "min": -2.0,
        "max": 150.0,
        "step" : 0.3
    },
    {
        "label": "Number input - int slider",
        "help": "default value is 20'",
        "type": "slider",
        "min": 0,
        "max": 100,
    },
]


st.write("before value 2 : ", st.session_state["input_items"])
st.write("before value 2 : ", input_arr)

output_arr = generate_inputs_and_return_values(st.session_state["input_items"], infos)
st.session_state.input_items = output_arr
st.session_state["input_items"] = output_arr

st.write("after value 2 : ", st.session_state["input_items"])
st.write("after value 2 : ", output_arr)






