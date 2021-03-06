import logging

logger = logging.getLogger(None if __name__ == '__main__' else __name__)


class ConstituencyTree:
    """
    Group together information from a constituency tree and expose convenient
    lookups.
    """

    def __init__(self, head2deps):
        """
        Initialise `ConstituencyTree`
        """
        self.head2deps = head2deps

        # Create the reverse too
        self.dep2heads = self.reverse_headdep_dict(head2deps)

        logger.debug("head2deps: {}".format(self.head2deps))
        logger.debug("dep2heads: {}".format(self.dep2heads))
        self._head2constituent = {}

    def __repr__(self):
        return self.__class__.__name__ + '({!r})'.format(self.head2deps)

    def __eq__(self, other):
        if isinstance(other, type(self)):
            return self.head2deps == other.head2deps
        return False

    @classmethod
    def from_naf(cls, nafobj, term_filter=lambda naf, t: True):
        """
        Initialise this ConstituencyTree from a NAF object

        Only keep terms where `term_filter(term)` evaluates True.

        :param nafobj:          NAF object from input
        :param term_filter:     filter for terms
        """
        unfiltered = cls.create_headdep_dict(nafobj)
        return cls(cls.filter_headdep_dict(
            unfiltered,
            lambda t: term_filter(nafobj, t)
        ))

    @staticmethod
    def reverse_headdep_dict(head2deps):
        """
        Create dep2heads from head2deps (or visa versa?)
        """
        dep2heads = {}
        for headID, deps in head2deps.items():
            for toID, relation in deps:
                dep2heads.setdefault(toID, set()).add((headID, relation))
        return dep2heads

    def get_direct_dependents(self, ID):
        """
        Get the term IDs of the terms directly dependent on `ID`.

        :param headID:  term ID to get direct dependents of
        :return:        a set of IDs that are direct dependents of `ID`
        """
        if ID in self.head2deps:
            return {ID for ID, _ in self.head2deps[ID]}

    def get_direct_parents(self, ID):
        """
        Get the term IDs of the terms of which `ID` is a direct dependent.

        :param headID:  term ID to get direct parents of
        :return:        a set of IDs that are direct parents of `ID`
        """
        if ID in self.dep2heads:
            return {ID for ID, _ in self.dep2heads[ID]}

    def get_constituent(self, ID):
        """
        Get the term IDs of the terms dependent on `ID`.

        Always contains `ID`, even if it is an unknown `ID`.

        :param headID:  term ID to get constituent of
        :return:        a set of IDs of terms that are dependents of `ID`
        """
        try:
            return self._head2constituent[ID]
        except KeyError:
            return self._get_constituent(ID, set())

    def _get_constituent(self, ID, parents):
        """
        Calculate the constituent if it is not in the cache

        :param head:      head to find constituent of
        :param parents:   term IDs that are already being calculated, thus
                          should not be recursed into
        :return:          set of term IDs that are in the constituent of `head`
        """
        if ID in parents:
            # Prevent loop
            return set()
        elif ID in self._head2constituent:
            # Use cache
            return self._head2constituent[ID]
        # Base case: direct dependents
        deps = {term_id for term_id, _ in self.head2deps.get(ID, [])}
        # Recursive step: call _get_constituent for every direct dependent
        parents.add(ID)
        deps.update(*(
            self._get_constituent(term_id, parents)
            for term_id in deps
        ))
        # Make sure ID itself is in it
        deps.add(ID)
        # Cache
        self._head2constituent[ID] = deps
        return deps

    @staticmethod
    def create_headdep_dict(nafobj):
        """
        Create dictionary of head to direct dependents

        :param nafobj:          NAF object from input
        :return:                head2deps
        """

        head2deps = {}
        for dep in nafobj.get_dependencies():
            head2deps.setdefault(dep.get_from(), set()).add(
                (dep.get_to(), dep.get_function())
            )
        return head2deps

    @staticmethod
    def filter_headdep_dict(head2deps, term_filter):
        """
        Only keep terms where `term_filter(term)` evaluates True.

        If a term is removed, the link (or function) information is handled as
        follows:

            from  --parent info-->  removed  --child info-->  to

        becomes

            from  --child info-->  to

        !! NB !! If a circular reference exists in the dependency tree, this
                 will stay in, even if some of the terms in the circular
                 reference are filtered out.

        :param head2deps:       {head: {(dep, function), ...}}
        :param term_filter:     filter for terms
        """
        dep2headIDs = {}
        for headID, deps in head2deps.items():
            for toID, _ in deps:
                dep2headIDs.setdefault(toID, []).append(headID)
        logger.debug("dep2headIDs: {}".format(dep2headIDs))
        filtered = {}
        for headID, deps in head2deps.items():
            # I don't have to do something with the deps that are filtered out,
            # because if they are leaves they can be left out and if they
            # aren't leaves they will also appear as headID and handled there.
            logger.debug("headID: {}".format(headID))
            deps = {
                (toID, relation)
                for toID, relation in deps
                if term_filter(toID)
            }
            logger.debug("deps: {}".format(deps))
            if term_filter(headID):
                if deps:
                    filtered.setdefault(headID, set()).update(deps)
            elif deps:
                # Delete the head by adding its dependents to the most shallow
                # head that isn't filtered out.
                stack = dep2headIDs.get(headID, [])
                been_in_stack = set(stack)
                super_heads = []
                while stack:
                    logger.debug("stack: {}".format(stack))
                    super_head = stack.pop()
                    if term_filter(super_head):
                        super_heads.append(super_head)
                    else:
                        add_to_stack = [
                            h for h in dep2headIDs.get(super_head, [])
                            if h not in been_in_stack
                        ]
                        been_in_stack.update(add_to_stack)
                        logger.debug("add_to_stack: {}".format(add_to_stack))
                        stack.extend(
                            add_to_stack
                        )
                for super_head in super_heads:
                    filtered.setdefault(super_head, set()).update(deps)

        return filtered
