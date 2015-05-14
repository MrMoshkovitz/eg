import os
import pydoc

from eg import color
from eg import substitute


# The file name suffix expected for example files.
EXAMPLE_FILE_SUFFIX = '.md'

# Version of eg itself.
# Also bump in setup.py.
VERSION = '0.1.0'

# Flags for showing where the examples for commands are coming from.
FLAG_ONLY_CUSTOM = '+'
FLAG_CUSTOM_AND_DEFAULT = '*'

# This flag indicates that we should use the fallback pager.
FLAG_FALLBACK = 'pydoc.pager'


def handle_program(program, config):
    default_file_path = None
    custom_file_path = None

    if has_default_entry_for_program(program, config):
        default_file_path = get_file_path_for_program(
            program,
            config.examples_dir
        )

    if has_custom_entry_for_program(program, config):
        custom_file_path = get_file_path_for_program(
            program,
            config.custom_dir
        )

    # Handle the case where we have nothing for them.
    if default_file_path is None and custom_file_path is None:
        print (
            'No entry found for ' +
            program +
            '. Run `eg --list` to see all available entries.'
        )
        return

    raw_contents = get_contents_from_files(
        default_file_path,
        custom_file_path
    )

    formatted_contents = get_formatted_contents(
        raw_contents,
        use_color=config.use_color,
        color_config=config.color_config,
        squeeze=config.squeeze,
        subs=config.subs
    )

    page_string(formatted_contents, config.pager_cmd)


def get_file_path_for_program(program, dir_to_search):
    """
    Return the file name and path for the program.

    examples_dir cannot be None

    Path is not guaranteed to exist. Just says where it should be if it
    existed. Paths must be fully expanded before being passed in (i.e. no ~ or
    variables).
    """
    if dir_to_search is None:
        raise TypeError('examples_dir cannot be None')
    else:
        result = os.path.join(dir_to_search, program + EXAMPLE_FILE_SUFFIX)
        return result


def has_default_entry_for_program(program, config):
    """Return True if has standard examples for program, else False."""
    if config.examples_dir:
        file_path = get_file_path_for_program(
            program,
            config.examples_dir
        )
        return os.path.isfile(file_path)
    else:
        return False


def has_custom_entry_for_program(program, config):
    """Return True if has custom examples for a program, else false."""
    if config.custom_dir:
        custom_path = get_file_path_for_program(
            program,
            config.custom_dir
        )
        return os.path.isfile(custom_path)
    else:
        return False


def get_contents_from_files(default_file_path, custom_file_path):
    """
    Take the paths to two files and return the contents as a string. If
    custom_file_path is valid, it will be shown before the contents of the
    default file.
    """
    file_data = ''

    if custom_file_path:
        file_data += _get_contents_of_file(custom_file_path)

    if default_file_path:
        file_data += _get_contents_of_file(default_file_path)

    return file_data


# def open_pager_for_file(
#     starting_contents=None,
#     use_color=False,
#     color_config=None,
#     pager_cmd=None,
#     squeeze=None,
#     subs=None
# ):
#     """
#     Apply formatting to the starting_contents as necessary and return the
#     result.
#     Open pager to file_path. If a custom_file_path is also included, it will be
#     shown before file_path in the same pager.
#     """
#     string_to_page = starting_contents

#     if use_color:
#         string_to_page = get_colorized_contents(string_to_page)

#     if squeeze:
#         string_to_page = get_squeezed_contents(string_to_page)

#     if subs:
#         string_to_page = get_substituted_contents(string_to_page, subs)

#     page_string(string_to_page, pager_cmd)


def page_string(str_to_page, pager_cmd):
    """
    Page str_to_page via the pager. Tries to do a bit of fail-safe checking. For
    example, if the command starts with less but less doesn't appear to be
    installed on the system, it will resort to the pydoc.pager method.
    """
    # By default, we expect the command to be `less -R`. If that is the
    # pager_cmd, but they don't have less on their machine, odds are they're
    # just using the default value. In this case the pager will fail, so we'll
    # just go via pydoc.pager, which tries to do smarter checking that we don't
    # want to bother trying to replicate.
    # import ipdb; ipdb.set_trace()
    use_fallback_page_function = False
    if pager_cmd is None:
        use_fallback_page_function = True
    elif pager_cmd == FLAG_FALLBACK:
        use_fallback_page_function = True
    elif pager_cmd.startswith('less'):
        # stealing this check from pydoc.getpager()
        if hasattr(os, 'system') and os.system('(less) 2>/dev/null') != 0:
            # no less!
            use_fallback_page_function = True

    if use_fallback_page_function:
        pydoc.pager(str_to_page)
    else:
        # Otherwise, obey the user.
        pydoc.pipepager(str_to_page, cmd=pager_cmd)


def _get_contents_of_file(path):
    """Get the contents of the file at path. The file must exist."""
    with open(path, 'r') as f:
        result = f.read()
        return result


def get_list_of_all_supported_commands(config):
    """
    Generate a list of all the commands that have examples known to eg. The
    format of the list is the command names. The fact that there are examples
    for 'cp', for example, would mean that 'cp' was in the list.

    The format of the list contains additional information to say if there are
    only default examples, only custom examples, or both:

        cp    (only default)
        cp *  (only custom)
        cp +  (default and custom)
    """
    default_files = []
    custom_files = []

    if config.examples_dir and os.path.isdir(config.examples_dir):
        default_files = os.listdir(config.examples_dir)
    if config.custom_dir and os.path.isdir(config.custom_dir):
        custom_files = os.listdir(config.custom_dir)

    # Now we get tricky. We're going to output the correct information by
    # iterating through each list only once. Keep pointers to our position in
    # the list. If they point to the same value, output that value with the
    # 'both' flag and increment both. Just one, output with the appropriate flag
    # and increment.

    ptr_default = 0
    ptr_custom = 0

    result = []

    def get_without_suffix(file_name):
        """
        Return the file name without the suffix, or the file name itself
        if it does not have the suffix.
        """
        return file_name.split(EXAMPLE_FILE_SUFFIX)[0]

    while ptr_default < len(default_files) and ptr_custom < len(custom_files):
        def_cmd = default_files[ptr_default]
        cus_cmd = custom_files[ptr_custom]

        if def_cmd == cus_cmd:
            # They have both
            result.append(
                get_without_suffix(def_cmd) +
                ' ' +
                FLAG_CUSTOM_AND_DEFAULT
            )
            ptr_default += 1
            ptr_custom += 1
        elif def_cmd < cus_cmd:
            # Only default, as default comes first.
            result.append(get_without_suffix(def_cmd))
            ptr_default += 1
        else:
            # Only custom
            result.append(get_without_suffix(cus_cmd) + ' ' + FLAG_ONLY_CUSTOM)
            ptr_custom += 1

    # Now just append.
    for i in range(ptr_default, len(default_files)):
        def_cmd = default_files[i]
        result.append(get_without_suffix(def_cmd))

    for i in range(ptr_custom, len(custom_files)):
        cus_cmd = custom_files[i]
        result.append(get_without_suffix(cus_cmd) + ' ' + FLAG_ONLY_CUSTOM)

    return result


def get_squeezed_contents(contents):
    """
    Squeeze the contents by removing blank lines between definition and example
    and remove duplicate blank lines except between sections.
    """
    line_between_example_code = substitute.Substitution(
        '\n\n    ',
        '\n    ',
        True
    )
    lines_between_examples = substitute.Substitution('\n\n\n', '\n\n', True)
    lines_between_sections = substitute.Substitution('\n\n\n\n', '\n\n\n', True)

    result = contents
    result = line_between_example_code.apply_and_get_result(result)
    result = lines_between_examples.apply_and_get_result(result)
    result = lines_between_sections.apply_and_get_result(result)
    return result


def get_colorized_contents(contents, color_config):
    """Colorize the contents based on the color_config."""
    colorizer = color.EgColorizer(color_config)
    result = colorizer.colorize_text(contents)
    return result


def get_substituted_contents(contents, substitutions):
    """
    Perform a list of substitutions and return the result.

    contents: the starting string on which to beging substitutions
    substitutions: list of Substitution objects to call, in order, with the
        result of the previous substitution.
    """
    result = contents
    for sub in substitutions:
        result = sub.apply_and_get_result(result)
    return result


def get_formatted_contents(
    raw_contents,
    use_color,
    color_config,
    squeeze,
    subs
):
    """
    Apply formatting to raw_contents and return the result. Formatting is
    applied in the order: color, squeeze, subs.
    """
    result = raw_contents

    if use_color:
        result = get_colorized_contents(result, color_config)

    if squeeze:
        result = get_squeezed_contents(result)

    if subs:
        result = get_substituted_contents(result, subs)

    return result
